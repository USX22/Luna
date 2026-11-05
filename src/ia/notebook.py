"""Luna's notebook: everything she explores or writes on her own (JSON lines)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path


class Notebook:
    def __init__(self, path: Path):
        self.path = path

    def entries(self, interest_id: str | None = None) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            items = [json.loads(line) for line in fh if line.strip()]
        return [e for e in items if interest_id is None or e.get("interest_id") == interest_id]

    def add(self, entry: dict, now: datetime | None = None) -> dict:
        entry = {"id": uuid.uuid4().hex[:8],
                 "ts": (now or datetime.now()).isoformat(timespec="seconds"),
                 "shared": False, **entry}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def count_on(self, day: datetime) -> int:
        prefix = day.date().isoformat()
        return sum(1 for e in self.entries() if e["ts"].startswith(prefix))

    def pending(self) -> list[dict]:
        return [e for e in self.entries() if e.get("share") and not e.get("shared")]

    def mark_shared(self, ids: set[str]) -> None:
        items = self.entries()
        for e in items:
            if e["id"] in ids:
                e["shared"] = True
        with self.path.open("w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in items)
