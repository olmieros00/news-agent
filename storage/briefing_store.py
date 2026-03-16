# Read/write MorningBriefing + Stories. Used by pipeline (write) and delivery (read).
# Step 13: delegate to backend when it supports save_briefing / get_latest_briefing (e.g. SQLiteBackend).
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from storage.backend import Backend

from models.briefing import MorningBriefing, Story


def _default_backend() -> "Backend":
    from config import get_settings
    from storage import SQLiteBackend
    return SQLiteBackend(get_settings().db_path)


def get_latest_briefing(
    backend: Optional["Backend"] = None,
) -> Tuple[Optional[MorningBriefing], List[Story]]:
    """Return latest briefing and its stories, or (None, [])."""
    if backend is None:
        backend = _default_backend()
    return backend.get_latest_briefing()


def save_briefing(
    briefing: MorningBriefing,
    stories: List[Story],
    backend: Optional["Backend"] = None,
) -> None:
    """Persist briefing and its stories."""
    if backend is None:
        backend = _default_backend()
    backend.save_briefing(briefing, stories)
