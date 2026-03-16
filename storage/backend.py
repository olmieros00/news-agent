# Abstract or common DB interface (raw, normalized, clusters).
# Step 2: raw table contract only; extend later for normalized/clusters/briefing.
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

# Avoid circular import; use TYPE_CHECKING
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from models.raw import RawRecord
    from models.briefing import MorningBriefing, Story


class Backend(ABC):
    """Storage backend. Implementations: SQLite, etc."""

    def __init__(self, dsn_or_path: str | None = None) -> None:
        self.dsn_or_path = dsn_or_path

    # ---- Raw ingestion (Step 2) ----

    @abstractmethod
    def insert_raw(self, records: list[RawRecord]) -> None:
        """Persist raw items. Caller assigns id to each record."""
        ...

    @abstractmethod
    def read_raw(
        self,
        source_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[RawRecord]:
        """Return raw records, optionally filtered by source and time range."""
        ...

    # ---- Maintenance ----

    def prune_raw(self, older_than: datetime) -> int:
        """Delete raw items with fetched_at < older_than. Return number of rows deleted. Default: no-op."""
        return 0

    # ---- Briefing (Step 13) ----

    def save_briefing(self, briefing: "MorningBriefing", stories: List["Story"]) -> None:
        """Persist briefing and its stories. Default: no-op; SQLiteBackend implements."""
        pass

    def get_latest_briefing(self) -> Tuple[Optional["MorningBriefing"], List["Story"]]:
        """Return latest briefing and stories, or (None, []). Default: (None, [])."""
        return None, []
