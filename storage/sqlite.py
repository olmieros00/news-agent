# SQLite implementation of Backend (raw table only for Step 2).
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from models.raw import RawRecord

from .backend import Backend
from models.briefing import MorningBriefing, Story

RAW_TABLE = "raw_items"
BRIEFINGS_TABLE = "briefings"
STORIES_TABLE = "stories"


class SQLiteBackend(Backend):
    """SQLite backend for raw ingestion. Creates DB and table on first use."""

    def __init__(self, dsn_or_path: str | None = None) -> None:
        super().__init__(dsn_or_path)
        self._path = dsn_or_path or ":memory:"
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        if self._path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:")
                self._init_schema_on(self._memory_conn)
            return self._memory_conn
        return sqlite3.connect(self._path)

    def _init_schema_on(self, c: sqlite3.Connection) -> None:
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {RAW_TABLE} (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        c.execute(f"CREATE INDEX IF NOT EXISTS idx_raw_source_id ON {RAW_TABLE}(source_id)")
        c.execute(f"CREATE INDEX IF NOT EXISTS idx_raw_fetched_at ON {RAW_TABLE}(fetched_at)")
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {BRIEFINGS_TABLE} (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {STORIES_TABLE} (
                id TEXT PRIMARY KEY,
                briefing_id TEXT NOT NULL,
                cluster_id TEXT NOT NULL,
                headline TEXT NOT NULL,
                date TEXT NOT NULL,
                body TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                vertical TEXT NOT NULL DEFAULT '',
                signal_type TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'standard',
                FOREIGN KEY (briefing_id) REFERENCES {BRIEFINGS_TABLE}(id)
            )
            """
        )
        c.execute(f"CREATE INDEX IF NOT EXISTS idx_stories_briefing ON {STORIES_TABLE}(briefing_id)")

    def _init_schema(self) -> None:
        if self._path == ":memory:":
            conn = self._conn()
            self._init_schema_on(conn)
            return
        with sqlite3.connect(self._path) as c:
            self._init_schema_on(c)

    def _serialize_payload(self, payload: object) -> str:
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, default=str)

    def _deserialize_payload(self, raw: str) -> object:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def insert_raw(self, records: list[RawRecord]) -> None:
        with self._conn() as c:
            for r in records:
                c.execute(
                    f"INSERT OR REPLACE INTO {RAW_TABLE} (id, source_id, fetched_at, payload) VALUES (?, ?, ?, ?)",
                    (
                        r.id,
                        r.source_id,
                        r.fetched_at.isoformat(),
                        self._serialize_payload(r.payload),
                    ),
                )

    def read_raw(
        self,
        source_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[RawRecord]:
        query = f"SELECT id, source_id, fetched_at, payload FROM {RAW_TABLE}"
        params: list[object] = []
        conditions: list[str] = []
        if source_id is not None:
            conditions.append("source_id = ?")
            params.append(source_id)
        if since is not None:
            conditions.append("fetched_at >= ?")
            params.append(since.isoformat())
        if until is not None:
            conditions.append("fetched_at <= ?")
            params.append(until.isoformat())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY fetched_at DESC"

        out: list[RawRecord] = []
        with self._conn() as c:
            for row in c.execute(query, params):
                rid, sid, fetched_at_str, payload_str = row
                out.append(
                    RawRecord(
                        id=rid,
                        source_id=sid,
                        fetched_at=datetime.fromisoformat(fetched_at_str),
                        payload=self._deserialize_payload(payload_str),
                    )
                )
        return out

    def prune_raw(self, older_than: datetime) -> int:
        """Delete raw items with fetched_at < older_than. Returns number of rows deleted."""
        cutoff = older_than.isoformat()
        with self._conn() as c:
            result = c.execute(
                f"DELETE FROM {RAW_TABLE} WHERE fetched_at < ?", (cutoff,)
            )
            return result.rowcount

    def save_briefing(self, briefing: MorningBriefing, stories: List[Story]) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as c:
            c.execute(
                f"INSERT OR REPLACE INTO {BRIEFINGS_TABLE} (id, date, created_at) VALUES (?, ?, ?)",
                (briefing.briefing_id, briefing.date, now),
            )
            for s in stories:
                c.execute(
                    f"INSERT OR REPLACE INTO {STORIES_TABLE} (id, briefing_id, cluster_id, headline, date, body, company, vertical, signal_type, source, priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (s.story_id, briefing.briefing_id, s.cluster_id, s.headline, s.date, s.body, s.company, s.vertical, s.signal_type, s.source, s.priority),
                )

    def get_latest_briefing(self) -> Tuple[Optional[MorningBriefing], List[Story]]:
        with self._conn() as c:
            row = c.execute(
                f"SELECT id, date, created_at FROM {BRIEFINGS_TABLE} ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None, []
            bid, bdate, _ = row
            briefing = MorningBriefing(briefing_id=bid, date=bdate, story_ids=[])
            rows = c.execute(
                f"SELECT id, cluster_id, headline, date, body, company, vertical, signal_type, source, priority FROM {STORIES_TABLE} WHERE briefing_id = ? ORDER BY id",
                (bid,),
            ).fetchall()
            stories = [
                Story(story_id=rid, cluster_id=cid, headline=h, date=d, body=b,
                      company=co or "", vertical=v or "", signal_type=st or "", source=src or "",
                      priority=p or "standard")
                for rid, cid, h, d, b, co, v, st, src, p in rows
            ]
            briefing.story_ids = [s.story_id for s in stories]
            return briefing, stories
