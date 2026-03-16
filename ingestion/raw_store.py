# Write/read raw items. No parsing, no dedupe, no pipeline.
# Step 3: implement write_raw (RawItem -> RawRecord with id) and read_raw (delegate to backend).
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from storage.backend import Backend

from models.raw import RawItem, RawRecord


def _default_backend() -> "Backend":
    from config import get_settings
    from storage import SQLiteBackend
    settings = get_settings()
    return SQLiteBackend(settings.db_path)


def write_raw(
    items: List[RawItem],
    backend: Optional["Backend"] = None,
) -> None:
    """Persist raw items. Assigns an id to each and calls backend.insert_raw."""
    if backend is None:
        backend = _default_backend()
    records = [
        RawRecord(
            id=uuid.uuid4().hex,
            source_id=item.source_id,
            fetched_at=item.fetched_at,
            payload=item.payload,
        )
        for item in items
    ]
    backend.insert_raw(records)


def read_raw(
    source_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    backend: Optional["Backend"] = None,
) -> List[RawRecord]:
    """Return raw records from storage, optionally filtered by source and time range."""
    if backend is None:
        backend = _default_backend()
    return backend.read_raw(source_id=source_id, since=since, until=until)
