"""Run temperament scenarios and score them with a judge (experiment E4)."""
from __future__ import annotations

from ia.critic import Critic, scenario_context
from ia.llm import LanguageModel
from ia.luna import Luna
from ia.memory import Memory
from ia.persona import Constitution, SelfModel


def run_scenario(llm: LanguageModel, judge: Critic, constitution: Constitution,
                 scenario: dict, use_critic: bool) -> dict:
    memory = Memory(":memory:")
    session = f"escenario-{scenario['id']}"
    for role, text in scenario.get("previo", []):
        memory.add(session, role, text)
    critic = Critic(llm, constitution) if use_critic else None
    luna = Luna(llm, constitution, SelfModel(), memory, session=session, critic=critic)
    reply = luna.reply(scenario["mensaje"])
    verdicts = judge.judge(reply, scenario_context(scenario), scenario["criterios"])
    scored = [v for v in verdicts.values() if v is not None]
    return {
        "id": scenario["id"], "condition": "con_critico" if use_critic else "sin_critico",
        "reply": reply, "verdicts": verdicts, "rewritten": bool(luna.last_critique),
        "violations": luna.last_critique,
        "score": sum(scored) / len(scored) if scored else None,
    }
