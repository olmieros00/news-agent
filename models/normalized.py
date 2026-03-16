# Single canonical schema for pipeline (title, body, url, dates, source_id).
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedItem:
    id: str
    source_id: str
    url: str
    title: str
    body_or_snippet: str
    published_at: datetime
    raw_id: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    # After translate step: English version for clustering and output (non-English sources)
    title_en: Optional[str] = None
    body_en: Optional[str] = None
