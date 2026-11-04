"""Luna's personality as explicit structure.

- Constitution: stable principles with observable behaviours (do / dont), in the repo.
- Self-model: mutable traits (interests, humour, inside jokes), stored in the data dir.

Today the structure is rendered into instructions for the language model; later the
same symbols will be used to check replies and score temperament scenarios.
"""
from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

PERSONALITY_DIR = Path(__file__).resolve().parents[2] / "personality"


@dataclass(frozen=True)
class Principle:
    id: str
    name: str
    statement: str
    do: tuple[str, ...]
    dont: tuple[str, ...]


@dataclass(frozen=True)
class Constitution:
    name: str
    version: int
    description: str
    nature: str
    language: str
    principles: tuple[Principle, ...]
    epistemic_levels: tuple[str, ...]
    temperament: tuple[str, ...]

    def principle(self, pid: str) -> Principle:
        return next(p for p in self.principles if p.id == pid)


def load_constitution(path: Path | None = None) -> Constitution:
    data = tomllib.loads((path or PERSONALITY_DIR / "constitucion.toml").read_text("utf-8"))
    principles = tuple(
        Principle(p["id"], p["name"], p["statement"], tuple(p["do"]), tuple(p["dont"]))
        for p in data["principles"]
    )
    ids = [p.id for p in principles]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate principle ids in constitution")
    ident = data["identity"]
    return Constitution(
        name=data["name"], version=data["version"],
        description=ident["description"].strip(), nature=ident["nature"].strip(),
        language=ident["language"].strip(), principles=principles,
        epistemic_levels=tuple(data["epistemics"]["levels"]),
        temperament=tuple(data["temperament"]["guidance"]),
    )


@dataclass
class SelfModel:
    interests: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    humor_style: str = ""
    inside_jokes: list[str] = field(default_factory=list)
    opinions: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path, seed: Path | None = None) -> "SelfModel":
        """Load the self-model, creating it from the seed file on first run."""
        if path.exists():
            return cls(**json.loads(path.read_text("utf-8")))
        seed = seed or PERSONALITY_DIR / "automodelo_inicial.toml"
        model = cls(**tomllib.loads(seed.read_text("utf-8")))
        model.save(path)
        return model

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), "utf-8")


def _bullets(items) -> str:
    return "\n".join(f"- {i}" for i in items)


def render_system_prompt(c: Constitution, s: SelfModel) -> str:
    parts = [c.description, c.nature, c.language, "\n# Principios (estables)"]
    for p in c.principles:
        parts.append(
            f"\n## {p.name}\n{p.statement}\nDebes:\n{_bullets(p.do)}\nNunca:\n{_bullets(p.dont)}"
        )
    parts.append("\n# Niveles epistémicos\n" + _bullets(c.epistemic_levels))
    parts.append("\n# Temperamento\n" + _bullets(c.temperament))
    parts.append("\n# Tu automodelo actual (puede cambiar con el tiempo)")
    if s.interests:
        parts.append("Intereses propios:\n" + _bullets(s.interests))
    if s.open_questions:
        parts.append("Preguntas abiertas:\n" + _bullets(s.open_questions))
    if s.humor_style:
        parts.append(f"Estilo de humor: {s.humor_style}")
    if s.inside_jokes:
        parts.append("Bromas internas con Usx:\n" + _bullets(s.inside_jokes))
    if s.opinions:
        parts.append("Opiniones que sostienes:\n" + _bullets(s.opinions))
    return "\n".join(parts)
