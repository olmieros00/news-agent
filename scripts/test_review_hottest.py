# Test: run pipeline up to rank and print top headlines with hotness metrics (coverage, regions, recency, score).
# Run from news-agent: python3 scripts/test_review_hottest.py
# Uses same data window and formula as run_full_pipeline (60% coverage, 25% diversity, 15% recency).
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

from config import get_settings
from ingestion import read_raw
from pipeline import normalize, translate_to_english, dedupe, cluster, rank
from pipeline.rank import score_breakdown
from storage import SQLiteBackend


def _headline_for_cluster(members, item_by_id):
    """Use only English-confirmed titles (title_en). Falls back to original only if none are translated."""
    en_titles = []
    all_titles = []
    for mid in members:
        item = item_by_id.get(mid)
        if not item:
            continue
        if (item.title_en or "").strip():
            en_titles.append(item.title_en.strip())
        if (item.title or "").strip():
            all_titles.append(item.title.strip())
    titles = en_titles if en_titles else all_titles
    if not titles:
        return "—"
    in_range = [t for t in titles if 5 <= len(t.split()) <= 12]
    candidates = in_range if in_range else titles
    return min(candidates, key=lambda t: len(t.split()))


def main() -> None:
    settings = get_settings()
    backend = SQLiteBackend(settings.db_path)
    since = datetime.utcnow() - timedelta(hours=settings.pipeline_hours_lookback)
    now = datetime.now(timezone.utc)

    print("Loading raw items (last {} hours)...".format(settings.pipeline_hours_lookback))
    raw = read_raw(since=since, backend=backend)
    if not raw:
        print("No raw items. Run the full pipeline first: python3 scripts/run_full_pipeline.py")
        return

    print("Normalize -> translate -> dedupe -> cluster -> rank...")
    normalized = normalize(raw)
    # Apply the same cap as run_full_pipeline --quick (1600 items).
    quick_cap = 1600
    if len(normalized) > quick_cap:
        normalized = sorted(
            normalized,
            key=lambda x: (x.published_at is None, -(x.published_at.timestamp() if x.published_at else 0)),
        )[:quick_cap]
    translated = translate_to_english(normalized)
    deduped = dedupe(translated)
    clusters = cluster(deduped)
    top_n = min(settings.top_n_stories, len(clusters))
    ranked = rank(clusters, deduped, top_n=top_n)

    item_by_id = {n.id: n for n in deduped}
    print()
    print("Formula: score = 0.65×coverage + 0.25×regions + 0.10×recency  (36h half-life)")
    print()
    print("--- Hottest headlines (by weighted score) ---")
    for i, c in enumerate(ranked, 1):
        members = [item_by_id[mid] for mid in c.member_ids if mid in item_by_id]
        headline = _headline_for_cluster(c.member_ids, item_by_id)
        b = score_breakdown(c, deduped, now)
        cov = b["coverage"]
        reg = b["region_count"]
        rec = b["recency_score"]
        sc = b["weighted_score"]
        latest_str = b["latest_utc"].strftime("%Y-%m-%d %H:%M") if b.get("latest_utc") else "—"
        print(f"  {i:2}. {headline[:70]}{'...' if len(headline) > 70 else ''}")
        print(f"      coverage={cov}  regions={reg}  recency={rec}  score={sc:.2f}  latest={latest_str} UTC")
        print(f"      story_id={c.cluster_id}")
    print()
    print("To expand a story: python3 scripts/test_expand_story.py <index_or_story_id>")


if __name__ == "__main__":
    main()
