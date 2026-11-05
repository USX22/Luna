"""Permission policy enforced in code (not in the prompt).

Levels (docs/vision.md §8):
  0 internal           - always allowed (thinking, notes)
  1 routine            - allowed autonomously only if Usx granted it
  2 costs or effects   - proposal for approval unless Usx granted it explicitly
  3 irreversible       - never autonomous; approval needs an explicit confirmation word

Every decision and result is appended to an audit log.
"""
from __future__ import annotations

import json
import tomllib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ALLOW, PROPOSE, DENY = "permitir", "proponer", "denegar"
CONFIRM_WORD = "CONFIRMO"

DEFAULT_POLICY = """# Permisos de Luna. Lo que no aparece aquí usa el nivel por defecto de cada herramienta.
# Niveles: 0 interno, 1 rutinario, 2 con costos o efectos, 3 irreversible o sensible.

[autonomia]
# Herramientas que puede usar sin preguntar (solo niveles 1 y 2; el nivel 3 nunca).
permitir = ["wikipedia", "arxiv"]
# Para que ejecute simulaciones en Python sin pedir permiso, agrega "python".
# Aviso: el ejecutor aísla fallos y bucles, pero NO es un sandbox de seguridad.

[niveles]
# Puedes subir el nivel de una herramienta (nunca bajarlo de su mínimo).
# python = 3

[privacidad]
# Términos que nunca deben salir de tu máquina en una búsqueda (nombres, lugares...).
# Los correos y teléfonos se bloquean siempre.
terminos = []
"""


@dataclass
class Policy:
    granted: set[str] = field(default_factory=set)
    overrides: dict[str, int] = field(default_factory=dict)
    private_terms: list[str] = field(default_factory=list)
    stopped: bool = False  # emergency stop (luna-alto): everything above level 0 denied

    @classmethod
    def load(cls, path: Path) -> "Policy":
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(DEFAULT_POLICY, "utf-8")
        from ia.safety import is_stopped
        data = tomllib.loads(path.read_text("utf-8"))
        return cls(set(data.get("autonomia", {}).get("permitir", [])),
                   dict(data.get("niveles", {})),
                   list(data.get("privacidad", {}).get("terminos", [])),
                   is_stopped(path.parent))

    def level(self, tool: str, minimum: int) -> int:
        return max(minimum, int(self.overrides.get(tool, minimum)))

    def decide(self, tool: str, minimum: int) -> str:
        level = self.level(tool, minimum)
        if level == 0:
            return ALLOW
        if self.stopped:
            return DENY
        if level >= 3:
            return PROPOSE
        return ALLOW if tool in self.granted else PROPOSE


class JsonlStore:
    def __init__(self, path: Path):
        self.path = path

    def all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def append(self, item: dict) -> dict:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item

    def rewrite(self, items: list[dict]) -> None:
        with self.path.open("w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(i, ensure_ascii=False) + "\n" for i in items)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Proposals(JsonlStore):
    """Actions waiting for Usx's approval."""

    def add(self, tool: str, args: dict, reason: str, level: int) -> dict:
        return self.append({"id": uuid.uuid4().hex[:6], "ts": now_iso(), "tool": tool,
                            "args": args, "reason": reason, "level": level,
                            "status": "pendiente", "result": None})

    def pending(self) -> list[dict]:
        return [p for p in self.all() if p["status"] == "pendiente"]

    def get(self, pid: str) -> dict | None:
        return next((p for p in self.all() if p["id"] == pid), None)

    def update(self, pid: str, **changes) -> None:
        items = self.all()
        for p in items:
            if p["id"] == pid:
                p.update(changes)
        self.rewrite(items)
