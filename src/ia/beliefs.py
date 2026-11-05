"""Symbolic belief store: explicit triples with epistemic status and provenance.

A belief is (holder, subject, relation, object, polarity). Symbolic rules, not the
language model, decide:
  - belief change: same holder, same triple, opposite polarity -> the old one is revised
  - disagreement: different holders, same triple, opposite polarity
  - reinforcement: same holder, same triple, same polarity -> no duplicate
"""
from __future__ import annotations

import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ia.agenda import normalize

LEVELS = ("sabemos", "podria_ser", "especulo", "opinion")
HOLDERS = ("usx", "luna")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS beliefs (
    id TEXT PRIMARY KEY, holder TEXT, subject TEXT, relation TEXT, object TEXT,
    polarity INTEGER, level TEXT, text TEXT, source TEXT, ts TEXT,
    status TEXT DEFAULT 'vigente', superseded_by TEXT, key TEXT
);
CREATE TABLE IF NOT EXISTS changes (
    holder TEXT, old_id TEXT, new_id TEXT, ts TEXT
);
"""


@dataclass(frozen=True)
class Belief:
    id: str
    holder: str
    subject: str
    relation: str
    object: str
    polarity: bool
    level: str
    text: str
    source: str
    ts: str
    status: str = "vigente"
    superseded_by: str | None = None

    def describe(self) -> str:
        neg = "" if self.polarity else "NO "
        return f"{self.subject} {neg}{self.relation} {self.object}"


def triple_key(subject: str, relation: str, obj: str) -> str:
    return "|".join(normalize(x) for x in (subject, relation, obj))


_COLS = "id, holder, subject, relation, object, polarity, level, text, source, ts, status, superseded_by"


def _row(r) -> Belief:
    return Belief(r[0], r[1], r[2], r[3], r[4], bool(r[5]), r[6], r[7], r[8], r[9], r[10], r[11])


class BeliefStore:
    def __init__(self, path: Path | str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.executescript(_SCHEMA)

    def add(self, holder: str, subject: str, relation: str, obj: str, polarity: bool,
            level: str = "opinion", text: str = "", source: str = "",
            ts: str | None = None) -> tuple[Belief | None, str]:
        """Insert a belief applying the symbolic rules.

        Returns (belief, event) where event is 'nueva', 'reforzada', 'cambio' or 'invalida'.
        """
        if holder not in HOLDERS or not (subject.strip() and relation.strip() and obj.strip()):
            return None, "invalida"
        level = level if level in LEVELS else "opinion"
        ts = ts or datetime.now().isoformat(timespec="seconds")
        key = triple_key(subject, relation, obj)
        current = self.db.execute(
            f"SELECT {_COLS} FROM beliefs WHERE holder=? AND key=? AND status='vigente'",
            (holder, key)).fetchone()
        if current and bool(current[5]) == polarity:
            self.db.execute("UPDATE beliefs SET ts=? WHERE id=?", (ts, current[0]))
            self.db.commit()
            return _row(current), "reforzada"
        bid = uuid.uuid4().hex[:8]
        self.db.execute(
            f"INSERT INTO beliefs ({_COLS}, key) VALUES (?,?,?,?,?,?,?,?,?,?,'vigente',NULL,?)",
            (bid, holder, subject.strip(), relation.strip(), obj.strip(), int(polarity),
             level, text, source, ts, key))
        event = "nueva"
        if current:
            self.db.execute("UPDATE beliefs SET status='revisada', superseded_by=? WHERE id=?",
                            (bid, current[0]))
            self.db.execute("INSERT INTO changes VALUES (?,?,?,?)", (holder, current[0], bid, ts))
            event = "cambio"
        self.db.commit()
        return self.get(bid), event

    def get(self, bid: str) -> Belief | None:
        r = self.db.execute(f"SELECT {_COLS} FROM beliefs WHERE id=?", (bid,)).fetchone()
        return _row(r) if r else None

    def current(self, holder: str | None = None) -> list[Belief]:
        rows = self.db.execute(
            f"SELECT {_COLS} FROM beliefs WHERE status='vigente' AND (? IS NULL OR holder=?) "
            "ORDER BY ts DESC", (holder, holder)).fetchall()
        return [_row(r) for r in rows]

    def about(self, text: str, k: int = 5) -> list[Belief]:
        """Current beliefs sharing words with the text (simple symbolic retrieval)."""
        words = set(re.findall(r"\w{4,}", normalize(text)))
        if not words:
            return []
        scored = []
        for b in self.current():
            bw = set(re.findall(r"\w{4,}", normalize(f"{b.subject} {b.relation} {b.object}")))
            overlap = len(words & bw)
            if overlap:
                scored.append((overlap, b.ts, b))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [b for _, _, b in scored[:k]]

    def changes(self, holder: str | None = None) -> list[tuple[Belief, Belief, str]]:
        rows = self.db.execute(
            "SELECT old_id, new_id, ts FROM changes WHERE (? IS NULL OR holder=?) ORDER BY ts DESC",
            (holder, holder)).fetchall()
        return [(self.get(o), self.get(n), ts) for o, n, ts in rows]

    def disagreements(self) -> list[tuple[Belief, Belief]]:
        rows = self.db.execute(
            f"SELECT a.id, b.id FROM beliefs a JOIN beliefs b ON a.key=b.key "
            "WHERE a.holder='usx' AND b.holder='luna' AND a.polarity != b.polarity "
            "AND a.status='vigente' AND b.status='vigente'").fetchall()
        return [(self.get(a), self.get(b)) for a, b in rows]
