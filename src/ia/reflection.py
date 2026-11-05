"""Reflection: Luna reviews recent conversations while Usx is away.

- Summarises each session (long-term episodic memory).
- Extracts beliefs (hers and Usx's) into the symbolic store.
- Proposes at most MAX_CHANGES changes to her self-model, each with a reason. Changes are
  versioned and reversible. The constitution is never touched: only whitelisted
  self-model fields can change.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from ia.agenda import Agenda
from ia.beliefs import BeliefStore
from ia.explore import identity_brief, parse_json_object
from ia.llm import LanguageModel
from ia.memory import Memory
from ia.persona import Constitution, SelfModel

MAX_CHANGES = 3
LIST_FIELDS = ("open_questions", "inside_jokes", "opinions")
MUTABLE_FIELDS = LIST_FIELDS + ("humor_style", "interests")
SUMMARY_SESSION = "reflexion"

REFLECT_PROMPT = """{identity}

Estás reflexionando a solas sobre una conversación reciente con Usx.

Conversación:
{transcript}

Tu automodelo actual:
{self_model}

Responde SOLO con JSON:
{{
 "resumen": "3-5 frases: qué pasó, qué importó, cómo quedó la relación",
 "creencias": [
   {{"quien": "usx" o "luna", "sujeto": "...", "relacion": "verbo o relación corta",
     "objeto": "...", "afirma": true o false,
     "nivel": "sabemos" | "podria_ser" | "especulo" | "opinion",
     "texto": "frase breve tal como se expresó"}}
 ],
 "automodelo": [
   {{"campo": "open_questions" | "inside_jokes" | "opinions" | "humor_style" | "interests",
     "accion": "agregar" | "quitar" | "reemplazar", "valor": "...", "motivo": "por qué"}}
 ]
}}
Solo creencias claramente expresadas (máximo 6). Cambios al automodelo solo si la
conversación de verdad los justifica (puede ser lista vacía, máximo {max_changes}).
"""


class SelfModelHistory:
    """Versioned history of self-model changes (JSON lines with full snapshots)."""

    def __init__(self, path: Path):
        self.path = path

    def versions(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def record(self, model: SelfModel, changes: list[dict], note: str = "") -> dict:
        version = {"version": len(self.versions()) + 1,
                   "ts": datetime.now().isoformat(timespec="seconds"),
                   "changes": changes, "note": note, "snapshot": asdict(model)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(version, ensure_ascii=False) + "\n")
        return version

    def snapshot(self, number: int) -> dict | None:
        return next((v["snapshot"] for v in self.versions() if v["version"] == number), None)


def apply_changes(model: SelfModel, changes: list[dict], agenda: Agenda | None = None
                  ) -> list[dict]:
    """Apply up to MAX_CHANGES whitelisted changes; return those actually applied."""
    applied = []
    for ch in changes:
        if len(applied) >= MAX_CHANGES:
            break
        field, action, value = ch.get("campo"), ch.get("accion"), str(ch.get("valor") or "").strip()
        if field not in MUTABLE_FIELDS or not value or not str(ch.get("motivo") or "").strip():
            continue
        if field == "humor_style":
            if action in ("reemplazar", "agregar"):
                model.humor_style = value
                applied.append(ch)
        elif field == "interests":
            if action == "agregar" and agenda is not None and agenda.add(value, origin="reflexion"):
                applied.append(ch)
        else:
            items: list[str] = getattr(model, field)
            if action == "agregar" and value not in items:
                items.append(value)
                applied.append(ch)
            elif action == "quitar" and value in items:
                items.remove(value)
                applied.append(ch)
    return applied


class Reflector:
    def __init__(self, llm: LanguageModel, constitution: Constitution, self_model: SelfModel,
                 memory: Memory, beliefs: BeliefStore, home: Path,
                 agenda: Agenda | None = None):
        self.llm, self.constitution, self.self_model = llm, constitution, self_model
        self.memory, self.beliefs, self.home, self.agenda = memory, beliefs, home, agenda
        self.history = SelfModelHistory(home / "automodelo_historial.jsonl")
        self.state_path = home / "reflexion.json"

    def _last_id(self) -> int:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text("utf-8"))["last_episode_id"]
        return 0

    def _save_last_id(self, value: int) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"last_episode_id": value}), "utf-8")

    def pending_sessions(self) -> dict[str, list]:
        rows = self.memory.db.execute(
            "SELECT id, ts, session, role, content FROM episodes WHERE id > ? "
            "AND role IN ('user','assistant') ORDER BY id", (self._last_id(),)).fetchall()
        sessions: dict[str, list] = {}
        for r in rows:
            sessions.setdefault(r[2], []).append(r)
        return sessions

    def reflect(self, max_chars: int = 6000) -> list[dict]:
        reports = []
        identity = identity_brief(self.constitution, self.self_model)
        last = self._last_id()
        for session, rows in self.pending_sessions().items():
            transcript = "\n".join(
                f"{'Usx' if r[3] == 'user' else 'Luna'}: {r[4]}" for r in rows)[-max_chars:]
            data = parse_json_object(self.llm.generate(REFLECT_PROMPT.format(
                identity=identity, transcript=transcript,
                self_model=json.dumps(asdict(self.self_model), ensure_ascii=False),
                max_changes=MAX_CHANGES), format="json"))
            last = max(last, rows[-1][0])
            if data is None:
                reports.append({"session": session, "error": "JSON inválido"})
                continue
            report = {"session": session, "beliefs": [], "changes": []}
            if data.get("resumen"):
                self.memory.add(SUMMARY_SESSION, "resumen",
                                f"[resumen de la conversación {rows[0][1][:10]}] {data['resumen']}")
                report["summary"] = data["resumen"]
            for c in (data.get("creencias") or [])[:6]:
                if not isinstance(c, dict):
                    continue
                belief, event = self.beliefs.add(
                    str(c.get("quien", "")).lower(), str(c.get("sujeto", "")),
                    str(c.get("relacion", "")), str(c.get("objeto", "")),
                    bool(c.get("afirma", True)), str(c.get("nivel", "opinion")),
                    str(c.get("texto", "")), f"sesion:{session}")
                if belief:
                    report["beliefs"].append((event, belief.holder, belief.describe()))
            changes = [c for c in (data.get("automodelo") or []) if isinstance(c, dict)]
            if changes and not self.history.versions():
                self.history.record(self.self_model, [], "estado inicial")
            applied = apply_changes(self.self_model, changes, self.agenda)
            if applied:
                self.self_model.save(self.home / "automodelo.json")
                if self.agenda:
                    self.agenda.save()
                self.history.record(self.self_model, applied, f"reflexión sobre {session}")
                report["changes"] = applied
            reports.append(report)
        self._save_last_id(last)
        return reports

    def revert(self, version: int) -> bool:
        snap = self.history.snapshot(version)
        if snap is None:
            return False
        restored = SelfModel(**snap)
        for field in asdict(restored):
            setattr(self.self_model, field, getattr(restored, field))
        self.self_model.save(self.home / "automodelo.json")
        self.history.record(self.self_model, [], f"revertido a la versión {version}")
        return True
