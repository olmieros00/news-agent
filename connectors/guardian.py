# Guardian Open Platform API. Fetches raw JSON only.
# Step 4: call Content API search, paginate, one RawItem per article (payload = full API result).
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models.raw import RawItem

from .base import BaseConnector


class GuardianConnector(BaseConnector):
    """Fetches articles from Guardian Content API search. One RawItem per result."""

    def __init__(self, api_key: str, base_url: str = "https://content.guardianapis.com") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def fetch(
        self,
        since: Optional[datetime] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[RawItem]:
        """Fetch articles from Guardian search. Paginates until all results for the date range are read."""
        if not self.api_key:
            return []
        config = config or {}
        from_date = since or (datetime.utcnow() - timedelta(hours=24))
        from_str = from_date.strftime("%Y-%m-%d")
        page_size = config.get("page_size", 50)
        max_pages = config.get("max_pages", 20)
        fetched_at = datetime.utcnow()
        items: List[RawItem] = []
        page = 1
        while page <= max_pages:
            url = f"{self.base_url}/search"
            params = {
                "api-key": self.api_key,
                "from-date": from_str,
                "page-size": page_size,
                "page": page,
                "show-fields": "headline,trailText,shortUrl",
            }
            try:
                import requests
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                if items:
                    break
                raise RuntimeError(f"Guardian API request failed: {e}") from e
            response = data.get("response") or {}
            results = response.get("results") or []
            for r in results:
                items.append(
                    RawItem(
                        source_id="guardian",
                        fetched_at=fetched_at,
                        payload=dict(r),
                    )
                )
            total_pages = response.get("pages", 0)
            if page >= total_pages or not results:
                break
            page += 1
        return items
