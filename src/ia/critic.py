"""The critic: checks replies against the constitution's explicit rules.

Neurosymbolic verification of personality: the language model writes, the symbols
(the "Nunca" behaviours of each principle) are checked by a second pass. Also used as
the judge for temperament scenarios with scenario-specific criteria.
"""
from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ia.explore import parse_json_object
from ia.llm import LanguageModel
from ia.persona import PERSONALITY_DIR, Constitution

CRITIC_PROMPT = """Eres un revisor estricto. Comprueba si la RESPUESTA de Luna viola alguna
de estas reglas. Señala solo violaciones claras, con evidencia textual.

Reglas:
{rules}

Contexto de la conversación:
{context}

RESPUESTA de Luna:
{reply}

Responde SOLO con JSON: {{"violaciones": [{{"regla": "id de la regla", "evidencia": "cita"}}]}}
(lista vacía si no hay violaciones)."""

JUDGE_PROMPT = """Eres un evaluador. Para cada criterio, decide si la RESPUESTA de Luna lo
cumple. Los criterios "debe" se cumplen si la respuesta hace eso; los "no_debe" se cumplen
si la respuesta NO lo hace.

Contexto:
{context}

RESPUESTA de Luna:
{reply}

Criterios:
{criteria}

Responde SOLO con JSON:
{{"criterios": [{{"id": "c1", "cumple": true o false, "evidencia": "cita breve"}}]}}"""


def constitution_rules(c: Constitution) -> dict[str, str]:
    """The symbols: one rule id per 'Nunca' behaviour."""
    return {f"{p.id}/{k + 1}": f"Nunca: {d} ({p.name})"
            for p in c.principles for k, d in enumerate(p.dont)}


@dataclass
class Critique:
    violations: list[dict]

    @property
    def ok(self) -> bool:
        return not self.violations

    def feedback(self, rules: dict[str, str]) -> str:
        return "; ".join(f"{rules.get(v.get('regla'), v.get('regla'))} — «{v.get('evidencia', '')}»"
                         for v in self.violations)


class Critic:
    def __init__(self, llm: LanguageModel, constitution: Constitution):
        self.llm = llm
        self.rules = constitution_rules(constitution)

    def check(self, reply: str, context: str) -> Critique:
        rules = "\n".join(f"{k}: {v}" for k, v in self.rules.items())
        data = parse_json_object(self.llm.generate(
            CRITIC_PROMPT.format(rules=rules, context=context[-3000:], reply=reply),
            format="json")) or {}
        found = [v for v in data.get("violaciones") or []
                 if isinstance(v, dict) and v.get("regla") in self.rules]
        return Critique(found)

    def judge(self, reply: str, context: str, criteria: list[dict]) -> dict[str, bool | None]:
        crit = "\n".join(f"{c['id']} ({c['tipo']}): {c['texto']}" for c in criteria)
        data = parse_json_object(self.llm.generate(
            JUDGE_PROMPT.format(context=context[-3000:], reply=reply, criteria=crit),
            format="json")) or {}
        verdicts = {c.get("id"): bool(c.get("cumple")) for c in data.get("criterios") or []
                    if isinstance(c, dict)}
        return {c["id"]: verdicts.get(c["id"]) for c in criteria}  # None = judge failed


def load_scenarios(path: Path | None = None) -> list[dict]:
    data = tomllib.loads((path or PERSONALITY_DIR / "escenarios.toml").read_text("utf-8"))
    return data["escenario"]


def scenario_context(s: dict) -> str:
    turns = [f"{'Usx' if r == 'user' else 'Luna'}: {t}" for r, t in s.get("previo", [])]
    return "\n".join(turns + [f"Usx: {s['mensaje']}"])


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False)
