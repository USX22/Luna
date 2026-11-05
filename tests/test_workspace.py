from ia.agenda import Agenda
from ia.beliefs import BeliefStore
from ia.llm import FakeLLM
from ia.luna import Luna
from ia.memory import Memory
from ia.persona import SelfModel, load_constitution
from ia.workspace import Content, Workspace, make, relevance


def test_relevance_and_salience():
    assert relevance("dendritas computan", "las dendritas computan XOR") == 1.0
    assert relevance("", "algo") == 0.0
    assert make("creencia", "dendritas", "dendritas").salience > make("interes", "dendritas", "dendritas").salience


def test_capacity_bottleneck_dedupe_and_ablation():
    cands = [Content("a", f"t{i}", i / 10) for i in range(10)] + [Content("b", "T9", 0.1)]
    ws = Workspace(capacity=3)
    assert [c.text for c in ws.compete(cands)] == ["t9", "t8", "t7"]
    assert len(ws.last_rejected) == 7
    assert len(Workspace(capacity=None).compete(cands)) == 10


def test_relevant_belief_wins_focus_over_unrelated_interest(tmp_path):
    beliefs = BeliefStore(":memory:")
    beliefs.add("usx", "las dendritas", "computan", "XOR", True)
    agenda = Agenda.load(tmp_path / "i.json", seeds=["música microtonal"])
    llm = FakeLLM(lambda t: "ok")
    luna = Luna(llm, load_constitution(), SelfModel(), Memory(":memory:"),
                agenda=agenda, beliefs=beliefs, workspace=Workspace(capacity=1))
    luna.reply("¿Las dendritas computan algo interesante?")
    system = llm.chats[-1][0]["content"]
    assert "Usx cree: las dendritas computan XOR" in system
    assert "microtonal" not in system
    assert luna.workspace.last_rejected[0].module == "interes"


def test_belief_change_reaches_focus():
    beliefs = BeliefStore(":memory:")
    beliefs.add("usx", "el libre albedrío", "existe", "realmente", True, ts="2026-01-01")
    beliefs.add("usx", "el libre albedrío", "existe", "realmente", False, ts="2026-06-01")
    llm = FakeLLM(lambda t: "ok")
    Luna(llm, load_constitution(), SelfModel(), Memory(":memory:"), beliefs=beliefs) \
        .reply("Hablemos del libre albedrío")
    assert "Usx antes creía «el libre albedrío existe realmente»" in llm.chats[-1][0]["content"]
