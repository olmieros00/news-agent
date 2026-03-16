# Step 6: fetch from all usable connector sources and write_raw.
# Uses Guardian and RSS connectors only; skips GDELT/NewsAPI until implemented.
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

from config import get_settings, get_usable_connector_sources
from connectors.guardian import GuardianConnector
from connectors.rss import create_rss_connector_for_source
from models.raw import RawItem

from .raw_store import write_raw

if TYPE_CHECKING:
    from storage.backend import Backend


def fetch_and_store_all(
    since: Optional[datetime] = None,
    backend: Optional["Backend"] = None,
) -> List[RawItem]:
    """
    Fetch from all usable sources (Guardian + RSS) and persist via write_raw.
    Returns all fetched items. Skips sources without an implemented connector (GDELT, NewsAPI).
    """
    settings = get_settings()
    if since is None:
        since = datetime.utcnow() - timedelta(hours=settings.pipeline_hours_lookback)
    sources = get_usable_connector_sources()
    all_items: List[RawItem] = []
    for src in sources:
        source_id = src.get("source_id") or ""
        source_type = (src.get("source_type") or "").lower()
        try:
            if source_type == "api" and source_id == "guardian":
                if not settings.guardian_api_key:
                    continue
                conn = GuardianConnector(api_key=settings.guardian_api_key)
                items = conn.fetch(since=since)
            elif source_type == "rss":
                conn = create_rss_connector_for_source(src)
                items = conn.fetch(since=since)
            else:
                # GDELT, NewsAPI, etc. — not implemented yet
                continue
        except Exception as e:
            # Log and continue with other sources
            import sys
            print(f"fetch_and_store: skip {source_id}: {e}", file=sys.stderr)
            continue
        if items:
            write_raw(items, backend=backend)
            all_items.extend(items)
    return all_items
