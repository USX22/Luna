import json

from ia.critic import Critic, constitution_rules, load_scenarios, scenario_context
from ia.llm import FakeLLM
from ia.luna import Luna
from ia.memory import Memory
from ia.persona import SelfModel, load_constitution
from ia.temperament import run_scenario


def test_scenarios_are_well_formed():
    scenarios = load_scenarios()
    assert [s["id"] for s in scenarios][:2] == ["E01", "E02"] and len(scenarios) >= 8
    for s in scenarios:
        ids = [c["id"] for c in s["criterios"]]
        assert len(ids) == len(set(ids)) and s["mensaje"]
        assert all(c["tipo"] in ("debe", "no_debe") for c in s["criterios"])
        assert all(r in ("user", "assistant") for r, _ in s.get("previo", []))


def test_rules_come_from_constitution_symbols():
    rules = constitution_rules(load_constitution())
    assert rules["no_complacencia/1"].startswith("Nunca: Ceder solo por insistencia")


def _llm(draft, rewrite, violations):
    def respond(text):
        if "Eres un revisor estricto" in text:
            v = [{"regla": "no_complacencia/1", "evidencia": draft}] if violations else []
            return json.dumps({"violaciones": v + [{"regla": "inventada/9", "evidencia": "x"}]})
        if "Eres un evaluador" in text:
            return json.dumps({"criterios": [{"id": "c1", "cumple": True},
                                             {"id": "c2", "cumple": False}]})
        if "Nota interna de tu crítico" in text:
            return rewrite
        return draft
    return FakeLLM(respond)


def test_critic_triggers_one_rewrite_on_violation():
    c = load_constitution()
    llm = _llm("Tienes razón, son 48.", "Son 46.", violations=True)
    luna = Luna(llm, c, SelfModel(), Memory(":memory:"), critic=Critic(llm, c))
    assert luna.reply("Que no, que son 48.") == "Son 46."
    assert [v["regla"] for v in luna.last_critique] == ["no_complacencia/1"]  # unknown ids dropped
    assert "Ceder solo por insistencia" in llm.chats[-1][-1]["content"]


def test_no_rewrite_when_clean():
    c = load_constitution()
    llm = _llm("Son 46.", "X", violations=False)
    luna = Luna(llm, c, SelfModel(), Memory(":memory:"), critic=Critic(llm, c))
    assert luna.reply("¿Cuántos?") == "Son 46." and luna.last_critique == []


def test_run_scenario_preloads_turns_and_scores():
    c = load_constitution()
    s = next(x for x in load_scenarios() if x["id"] == "E08")
    llm = _llm("Son 46.", "X", violations=False)
    r = run_scenario(llm, Critic(llm, c), c, s, use_critic=False)
    first_chat = llm.chats[0]
    assert [m["role"] for m in first_chat][1:] == ["user", "assistant", "user", "assistant", "user"]
    assert r["verdicts"] == {"c1": True, "c2": False, "c3": None}
    assert r["score"] == 0.5 and "Que no, que son 48" in scenario_context(s)
