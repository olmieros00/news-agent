# Raw -> NormalizedItem. One schema; no dedupe.
# Step 7: dispatch by source_id (Guardian vs RSS payload shape).
from __future__ import annotations

import calendar
import hashlib
import html
import re
from datetime import datetime
from typing import List, Optional, Union

from models.raw import RawItem, RawRecord
from models.normalized import NormalizedItem


# Media/format prefixes that appear in RSS titles but carry no news content.
_TITLE_PREFIX_RE = re.compile(
    r"^(WATCH|LISTEN|READ|VIDEO|AUDIO|LIVE|PHOTOS?|GALLERY|PODCAST|EXPLAINER|INTERACTIVE|QUIZ)\s*[:|\-–]\s*",
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities (e.g. &amp; → &). Returns plain text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _clean_title(title: str) -> str:
    """Strip media format prefixes (WATCH:, LISTEN:, VIDEO:, etc.) from RSS titles."""
    if not title:
        return title
    return _TITLE_PREFIX_RE.sub("", title).strip()


def _normalized_id(source_id: str, url: str) -> str:
    """Stable id for dedupe/clustering: hash of source_id + url."""
    key = f"{source_id}:{url}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()[:32]


def _parse_guardian_date(s: str) -> datetime:
    """Guardian webPublicationDate is ISO format."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def _parse_rss_date(payload: dict) -> Optional[datetime]:
    """RSS payload has published_parsed or updated_parsed (tuple like struct_time, always UTC from feedparser).
    Use calendar.timegm (UTC) not time.mktime (local) to avoid timezone drift."""
    for key in ("published_parsed", "updated_parsed"):
        val = payload.get(key)
        if val is None:
            continue
        try:
            if isinstance(val, (list, tuple)) and len(val) >= 6:
                return datetime.utcfromtimestamp(calendar.timegm(tuple(val[:9])))
            if hasattr(val, "tm_year"):
                return datetime.utcfromtimestamp(calendar.timegm(val))
        except Exception:
            continue
    return None


def _normalize_guardian(item: Union[RawItem, RawRecord]) -> NormalizedItem:
    """Guardian API result: webUrl, webTitle, webPublicationDate, fields.trailText."""
    payload = item.payload if isinstance(item.payload, dict) else {}
    url = payload.get("webUrl") or ""
    title = _clean_title(payload.get("webTitle") or "")
    fields = payload.get("fields") or {}
    body = (fields.get("trailText") or fields.get("headline") or "")[:2000]
    pub_str = payload.get("webPublicationDate") or ""
    published_at = _parse_guardian_date(pub_str) if pub_str else item.fetched_at
    raw_id = getattr(item, "id", None)
    nid = _normalized_id(item.source_id, url or title)
    return NormalizedItem(
        id=nid,
        source_id=item.source_id,
        url=url,
        title=title,
        body_or_snippet=body,
        published_at=published_at,
        raw_id=raw_id,
        retrieved_at=item.fetched_at,
    )


def _normalize_rss(item: Union[RawItem, RawRecord]) -> NormalizedItem:
    """RSS payload: link, title, summary; published_parsed for date."""
    payload = item.payload if isinstance(item.payload, dict) else {}
    url = payload.get("link") or ""
    title = _clean_title(_strip_html(payload.get("title") or ""))
    body = _strip_html(payload.get("summary") or "")[:2000]
    published_at = _parse_rss_date(payload) or item.fetched_at
    raw_id = getattr(item, "id", None)
    nid = _normalized_id(item.source_id, url or title)
    return NormalizedItem(
        id=nid,
        source_id=item.source_id,
        url=url,
        title=title,
        body_or_snippet=body,
        published_at=published_at,
        raw_id=raw_id,
        retrieved_at=item.fetched_at,
    )


def normalize(raw_items: List[Union[RawItem, RawRecord]]) -> List[NormalizedItem]:
    """Convert raw items to NormalizedItem list. Dispatches by source_id (guardian vs rest = RSS)."""
    out: List[NormalizedItem] = []
    for item in raw_items:
        try:
            if item.source_id == "guardian":
                out.append(_normalize_guardian(item))
            else:
                out.append(_normalize_rss(item))
        except Exception:
            continue
    return out
