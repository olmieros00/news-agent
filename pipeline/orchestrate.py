# Orchestration: single entry point for the full pipeline (fetch optional, then read -> normalize -> ... -> save briefing).
# Used by scripts and (later) schedulers or Telegram layer. No Telegram formatting here.
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, List, Optional, TYPE_CHECKING

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from models.briefing import MorningBriefing, Story


@dataclass
class PipelineResult:
    """Result of a pipeline run: briefing and stories that were saved."""
    briefing: "MorningBriefing"
    stories: List["Story"]
    raw_count: int
    normalized_count: int
    deduped_count: int
    cluster_count: int
    ranked_count: int


def run_pipeline(
    backend: Any,
    *,
    fetch: bool = True,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    hours_lookback: Optional[int] = None,
    max_items: Optional[int] = None,
    top_n_stories: int = 10,
) -> Optional[PipelineResult]:
    """
    Run the full pipeline: optionally fetch and store raw, then read -> normalize -> translate
    -> dedupe -> cluster -> rank -> generate -> save briefing.

    Args:
        backend: Storage backend (e.g. SQLiteBackend) for raw and briefing.
        fetch: If True, call fetch_and_store_all before reading raw.
        since: Start of time window for raw items. If None, uses hours_lookback from now.
        until: End of time window. If None, uses now (UTC).
        hours_lookback: Used when since is None (default 24).
        max_items: Cap on items for translate+cluster (e.g. 800 for --quick, or settings value). 0 = no cap.
        top_n_stories: Max number of stories in the briefing.

    Returns:
        PipelineResult with briefing and stories, or None if no raw items (nothing to process).
    """
    from config import get_settings, get_source_registry
    from ingestion import fetch_and_store_all, read_raw
    from pipeline import normalize, translate_to_english, dedupe, cluster, rank, generate_stories
    from storage.briefing_store import save_briefing

    settings = get_settings()
    if hours_lookback is None:
        hours_lookback = settings.pipeline_hours_lookback
    if since is None:
        since = datetime.utcnow() - timedelta(hours=hours_lookback)
    # `until` is intentionally not set here: it is computed AFTER the fetch so newly-stored
    # items are always included. Passing `until=None` means "up to now" (no upper bound).

    # Prune raw items older than keep_days (default 3) to prevent unbounded DB growth.
    keep_days = getattr(settings, "db_keep_days", None) or 3
    prune_cutoff = datetime.utcnow() - timedelta(days=keep_days)
    deleted = backend.prune_raw(prune_cutoff)
    if deleted:
        log.info("Pruned %d raw items older than %s days.", deleted, keep_days)

    if fetch:
        fetch_and_store_all(backend=backend)

    # Compute `until` after the fetch so items stored during this run are included.
    if until is None:
        until = datetime.utcnow()

    raw = read_raw(since=since, until=until, backend=backend)
    if not raw:
        return None

    normalized = normalize(raw)
    cap = max_items if max_items is not None else (getattr(settings, "pipeline_max_items", 0) or 0)
    if cap > 0 and len(normalized) > cap:
        normalized = sorted(
            normalized,
            key=lambda x: (x.published_at is None, -(x.published_at.timestamp() if x.published_at else 0)),
        )[:cap]

    translated = translate_to_english(normalized)
    deduped = dedupe(translated)
    clusters = cluster(deduped)
    top_n = min(top_n_stories, len(clusters))
    ranked = rank(clusters, deduped, top_n=top_n)
    stories = generate_stories(ranked, deduped, get_source_registry())

    from models.briefing import MorningBriefing
    briefing = MorningBriefing(
        briefing_id=uuid.uuid4().hex,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        story_ids=[s.story_id for s in stories],
    )
    save_briefing(briefing, stories, backend=backend)


    return PipelineResult(
        briefing=briefing,
        stories=stories,
        raw_count=len(raw),
        normalized_count=len(normalized),
        deduped_count=len(deduped),
        cluster_count=len(clusters),
        ranked_count=len(ranked),
    )
