# RSS/Atom/XML feeds. Fetches raw feed content only.
# Step 5: one connector that takes source config (endpoint_url, source_id), returns list[RawItem].
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from models.raw import RawItem

from .base import BaseConnector


def _parse_feed_date(entry: Any) -> Optional[datetime]:
    """Get published/updated date from feed entry; return None if missing or unparseable.
    feedparser returns struct_time in UTC; use calendar.timegm (UTC) not time.mktime (local)."""
    try:
        import calendar
        for key in ("published_parsed", "updated_parsed"):
            val = getattr(entry, key, None)
            if val is None:
                continue
            if hasattr(val, "tm_year") or isinstance(val, (list, tuple)):
                return datetime.utcfromtimestamp(calendar.timegm(val))
        return None
    except Exception:
        return None


class RSSConnector(BaseConnector):
    """Fetches a single RSS/Atom feed. Config must include endpoint_url and source_id."""

    def __init__(self, source_id: str, endpoint_url: str) -> None:
        self.source_id = source_id
        self.endpoint_url = endpoint_url

    def fetch(
        self,
        since: Optional[datetime] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[RawItem]:
        """Fetch feed; one RawItem per entry. Payload = dict of entry fields for downstream normalization."""
        try:
            import feedparser
        except ImportError as e:
            raise RuntimeError("feedparser required for RSS connector; pip install feedparser") from e
        try:
            # feedparser has no native timeout; fetch with requests first, then parse the response text.
            import requests as _requests
            resp = _requests.get(
                self.endpoint_url,
                headers={"User-Agent": "NewsAgent/1.0"},
                timeout=15,
            )
            resp.raise_for_status()
            parsed = feedparser.parse(resp.text)
        except Exception as e:
            raise RuntimeError(f"RSS fetch failed for {self.endpoint_url}: {e}") from e
        fetched_at = datetime.utcnow()
        items: List[RawItem] = []
        for entry in getattr(parsed, "entries", []):
            # Store a dict representation for normalization layer (not raw XML).
            payload = {
                "title": getattr(entry, "title", "") or "",
                "link": getattr(entry, "link", "") or "",
                "summary": getattr(entry, "summary", "") or getattr(entry, "description", "") or "",
                "published": getattr(entry, "published", ""),
                "updated": getattr(entry, "updated", ""),
                "id": getattr(entry, "id", ""),
                "published_parsed": getattr(entry, "published_parsed", None),
                "updated_parsed": getattr(entry, "updated_parsed", None),
            }
            # Optional: filter by since (if entry has date)
            entry_dt = _parse_feed_date(entry)
            if since and entry_dt and entry_dt < since:
                continue
            items.append(
                RawItem(
                    source_id=self.source_id,
                    fetched_at=fetched_at,
                    payload=payload,
                )
            )
        return items


def create_rss_connector_for_source(source_config: Dict[str, Any]) -> RSSConnector:
    """Build RSSConnector from registry source config. Needs source_id and endpoint_url."""
    source_id = source_config.get("source_id") or "unknown"
    endpoint_url = source_config.get("endpoint_url") or ""
    if not endpoint_url:
        raise ValueError(f"RSS source {source_id} has no endpoint_url")
    return RSSConnector(source_id=source_id, endpoint_url=endpoint_url)
