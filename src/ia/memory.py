"""Episodic memory: every conversational turn, stored locally in SQLite.

Usx can search and delete memories (memory is not surveillance).
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    session TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
    content, content='episodes', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
    INSERT INTO episodes_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
    INSERT INTO episodes_fts(episodes_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;
"""

_WORD_RE = re.compile(r"\w{3,}", re.UNICODE)


@dataclass(frozen=True)
class Episode:
    id: int
    ts: str
    session: str
    role: str
    content: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Memory:
    def __init__(self, path: Path | str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.executescript(_SCHEMA)

    def add(self, session: str, role: str, content: str, ts: str | None = None) -> int:
        cur = self.db.execute(
            "INSERT INTO episodes (ts, session, role, content) VALUES (?, ?, ?, ?)",
            (ts or _now(), session, role, content),
        )
        self.db.commit()
        return cur.lastrowid

    def recent(self, session: str, n: int) -> list[Episode]:
        rows = self.db.execute(
            "SELECT id, ts, session, role, content FROM episodes WHERE session = ? "
            "ORDER BY id DESC LIMIT ?", (session, n),
        ).fetchall()
        return [Episode(*r) for r in reversed(rows)]

    def search(self, query: str, k: int = 5, exclude_session: str | None = None) -> list[Episode]:
        """Full-text search (any word of 3+ letters, accent-insensitive), best first."""
        words = _WORD_RE.findall(query.lower())
        if not words:
            return []
        match = " OR ".join(f'"{w}"' for w in dict.fromkeys(words))
        rows = self.db.execute(
            "SELECT e.id, e.ts, e.session, e.role, e.content FROM episodes_fts f "
            "JOIN episodes e ON e.id = f.rowid WHERE episodes_fts MATCH ? "
            "AND (? IS NULL OR e.session != ?) ORDER BY bm25(episodes_fts) LIMIT ?",
            (match, exclude_session, exclude_session, k),
        ).fetchall()
        return [Episode(*r) for r in rows]

    def forget(self, episode_id: int) -> bool:
        cur = self.db.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
        self.db.commit()
        return cur.rowcount > 0

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
