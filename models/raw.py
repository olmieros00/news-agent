# Raw item (in-memory) and raw record (stored). Opaque payload.
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class RawItem:
    source_id: str
    fetched_at: datetime
    payload: Any  # JSON dict or XML string


@dataclass
class RawRecord(RawItem):
    id: str
