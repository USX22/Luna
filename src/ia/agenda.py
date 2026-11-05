"""Luna's own interests, with curiosity modelled as learning progress.

Priority follows Oudeyer & Kaplan's idea: spend time where recent exploration produced
progress; new interests start optimistic; interests that stop yielding progress go
dormant (boredom) and may be revived later.
"""
from __future__ import annotations

import json
import math
import random
import re
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

MAX_ACTIVE = 7
NEW_INTEREST_PROGRESS = 0.6  # optimism for unexplored interests
BOREDOM_WINDOW = 3
BOREDOM_THRESHOLD = 0.2
REVIVE_PROBABILITY = 0.1
MAX_QUESTIONS = 8


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text)).strip()


@dataclass
class Interest:
    id: str
    topic: str
    origin: str = "semilla"  # semilla | propio | usx
    parent: str | None = None
    questions: list[str] = field(default_factory=list)
    sessions: int = 0
    last_explored: str | None = None
    progress: list[float] = field(default_factory=list)
    status: str = "activo"  # activo | dormido
    created: str = ""

    def learning_progress(self) -> float:
        recent = self.progress[-BOREDOM_WINDOW:]
        return sum(recent) / len(recent) if recent else NEW_INTEREST_PROGRESS

    def days_since_explored(self, now: datetime) -> float:
        if not self.last_explored:
            return 7.0
        return max(0.0, (now - datetime.fromisoformat(self.last_explored)).total_seconds() / 86400)


class Agenda:
    def __init__(self, path: Path, interests: list[Interest]):
        self.path = path
        self.interests = interests

    @classmethod
    def load(cls, path: Path, seeds: list[str] = ()) -> "Agenda":
        if path.exists():
            data = json.loads(path.read_text("utf-8"))
            return cls(path, [Interest(**d) for d in data])
        agenda = cls(path, [])
        for topic in seeds:
            agenda.add(topic, origin="semilla")
        agenda.save()
        return agenda

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(i) for i in self.interests],
                                        ensure_ascii=False, indent=2), "utf-8")

    def active(self) -> list[Interest]:
        return [i for i in self.interests if i.status == "activo"]

    def get(self, interest_id: str) -> Interest | None:
        return next((i for i in self.interests if i.id == interest_id), None)

    def add(self, topic: str, origin: str, parent: str | None = None,
            now: datetime | None = None) -> Interest | None:
        """Add an interest unless it already exists or the active cap is reached."""
        topic = topic.strip()
        if not topic or any(normalize(i.topic) == normalize(topic) for i in self.interests):
            return None
        if len(self.active()) >= MAX_ACTIVE:
            return None
        interest = Interest(uuid.uuid4().hex[:8], topic, origin, parent,
                            created=(now or datetime.now()).isoformat(timespec="seconds"))
        self.interests.append(interest)
        return interest

    def priority(self, interest: Interest, now: datetime) -> float:
        staleness = min(interest.days_since_explored(now), 7.0) / 7.0
        return interest.learning_progress() + 0.15 * staleness

    def choose(self, rng: random.Random, now: datetime, policy: str = "progreso",
               temperature: float = 0.15) -> Interest | None:
        self._maybe_revive(rng)
        candidates = self.active()
        if not candidates:
            return None
        if policy == "aleatoria":
            return rng.choice(candidates)
        weights = [math.exp(self.priority(i, now) / temperature) for i in candidates]
        return rng.choices(candidates, weights=weights, k=1)[0]

    def _maybe_revive(self, rng: random.Random) -> None:
        dormant = [i for i in self.interests if i.status == "dormido"]
        if dormant and (not self.active() or (len(self.active()) < MAX_ACTIVE
                                               and rng.random() < REVIVE_PROBABILITY)):
            revived = rng.choice(dormant)
            revived.status = "activo"
            revived.progress.append(NEW_INTEREST_PROGRESS)  # a fresh look

    def record(self, interest: Interest, progress: float, new_questions: list[str],
               answered: str | None, now: datetime) -> None:
        interest.sessions += 1
        interest.last_explored = now.isoformat(timespec="seconds")
        interest.progress.append(round(progress, 3))
        known = {normalize(q) for q in interest.questions}
        if answered:
            interest.questions = [q for q in interest.questions
                                  if normalize(q) != normalize(answered)]
        for q in new_questions:
            if q.strip() and normalize(q) not in known:
                interest.questions.append(q.strip())
                known.add(normalize(q))
        interest.questions = interest.questions[-MAX_QUESTIONS:]
        recent = interest.progress[-BOREDOM_WINDOW:]
        if len(recent) == BOREDOM_WINDOW and sum(recent) / BOREDOM_WINDOW < BOREDOM_THRESHOLD:
            interest.status = "dormido"
