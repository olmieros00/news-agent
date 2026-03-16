# Remove exact and near-duplicate normalized items.
# Step 9: exact by URL; then drop items with same normalized title (lower, stripped).
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from models.normalized import NormalizedItem


def _aware_dt(d: datetime) -> datetime:
    if d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d


def _normalize_title(title: str) -> str:
    """Lowercase, strip, collapse spaces for comparison."""
    return " ".join((title or "").lower().split())


def dedupe(normalized_items: List[NormalizedItem]) -> List[NormalizedItem]:
    """
    Exact dedupe by URL (keep first). Then near-dupe by normalized title:
    if two items have the same normalized title, keep the one with earlier published_at.
    """
    if not normalized_items:
        return []
    seen_urls: set[str] = set()
    seen_titles: dict[str, NormalizedItem] = {}
    out: List[NormalizedItem] = []
    # Sort by published_at desc so we keep the "newest" when we dedupe by URL
    for item in sorted(normalized_items, key=lambda x: _aware_dt(x.published_at), reverse=True):
        url_key = (item.url or "").strip()
        if url_key and url_key in seen_urls:
            continue
        if url_key:
            seen_urls.add(url_key)
        title_key = _normalize_title(item.title_en or item.title)
        if title_key and len(title_key) > 10:
            existing = seen_titles.get(title_key)
            if existing is not None:
                # Keep the one with earlier published_at (more canonical)
                if item.published_at >= existing.published_at:
                    continue
                out = [x for x in out if x.id != existing.id]
                seen_titles[title_key] = item
            else:
                seen_titles[title_key] = item
        out.append(item)
    return out
