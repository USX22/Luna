"""Global workspace (Baars; Dehaene): modules compete for a limited-capacity focus.

Each module proposes contents with a salience = module prior + relevance to the cue.
Only the top-`capacity` contents are broadcast to the language model; the rest stay
unconscious, so to speak. The last selection is kept so it can be inspected (/foco)
and compared with what Luna *says* she is focused on (line B4: self-model accuracy).
capacity=None disables the bottleneck (ablation).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ia.agenda import normalize

_WORD_RE = re.compile(r"\w{4,}", re.UNICODE)

PRIORS = {
    "memoria": 0.30,
    "resumen": 0.30,
    "creencia": 0.35,
    "cambio": 0.25,
    "desacuerdo": 0.30,
    "interes": 0.20,
}

LABELS = {
    "memoria": "Recuerdo",
    "resumen": "Recuerdo (resumen)",
    "creencia": "Creencia",
    "cambio": "Cambio de creencia",
    "desacuerdo": "Desacuerdo entre ustedes",
    "interes": "Interés propio",
}


def words(text: str) -> set[str]:
    return set(_WORD_RE.findall(normalize(text)))


def relevance(cue: str, text: str) -> float:
    """Fraction of the cue's content words that appear in the text."""
    cw = words(cue)
    return len(cw & words(text)) / len(cw) if cw else 0.0


@dataclass(frozen=True)
class Content:
    module: str
    text: str
    salience: float

    def render(self) -> str:
        return f"- {LABELS.get(self.module, self.module)}: {self.text}"


def make(module: str, text: str, cue: str, bonus: float = 0.0) -> Content:
    return Content(module, text, round(PRIORS.get(module, 0.2) + relevance(cue, text) + bonus, 3))


@dataclass
class Workspace:
    capacity: int | None = 8
    last_selected: list[Content] = field(default_factory=list)
    last_rejected: list[Content] = field(default_factory=list)

    def compete(self, candidates: list[Content]) -> list[Content]:
        unique: dict[str, Content] = {}
        for c in candidates:
            key = normalize(c.text)
            if key not in unique or unique[key].salience < c.salience:
                unique[key] = c
        ranked = sorted(unique.values(), key=lambda c: c.salience, reverse=True)
        cut = len(ranked) if self.capacity is None else self.capacity
        self.last_selected, self.last_rejected = ranked[:cut], ranked[cut:]
        return self.last_selected
