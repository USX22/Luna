import json

from ia.agenda import Agenda
from ia.beliefs import BeliefStore
from ia.llm import FakeLLM
from ia.memory import Memory
from ia.persona import SelfModel, load_constitution
from ia.reflection import MAX_CHANGES, Reflector, apply_changes


# --- symbolic beliefs ------------------------------------------------------

def test_belief_rules_new_reinforced_change_and_disagreement():
    b = BeliefStore(":memory:")
    old, e1 = b.add("usx", "Las dendritas", "computan", "XOR", True, ts="2026-01-01")
    _, e2 = b.add("usx", "las dendritas", "Computan", "xor", True, ts="2026-02-01")
    new, e3 = b.add("usx", "las dendritas", "computan", "XOR", False, ts="2026-03-01")
    assert (e1, e2, e3) == ("nueva", "reforzada", "cambio")
    assert b.get(old.id).status == "revisada" and b.get(old.id).superseded_by == new.id
    (before, after, ts), = b.changes("usx")
    assert before.polarity and not after.polarity and ts == "2026-03-01"
    b.add("luna", "las dendritas", "computan", "XOR", True)
    (u, l), = b.disagreements()
    assert u.holder == "usx" and l.holder == "luna"
    assert b.add("alguien", "a", "b", "c", True)[1] == "invalida"


def test_belief_retrieval_by_words():
    b = BeliefStore(":memory:")
    b.add("usx", "la conciencia", "requiere", "espacio de trabajo global", True)
    b.add("usx", "el café", "mejora", "la memoria", False)
    hits = b.about("¿Qué opinas de la conciencia?")
    assert [h.subject for h in hits] == ["la conciencia"]
    assert any(x.describe() == "el café NO mejora la memoria" for x in b.current("usx"))


# --- self-model changes ----------------------------------------------------

def test_apply_changes_whitelist_cap_and_reason_required(tmp_path):
    m = SelfModel(opinions=["vieja"])
    agenda = Agenda(tmp_path / "i.json", [])
    changes = [
        {"campo": "principios", "accion": "agregar", "valor": "obedecer", "motivo": "x"},
        {"campo": "opinions", "accion": "agregar", "valor": "nueva", "motivo": ""},
        {"campo": "inside_jokes", "accion": "agregar", "valor": "la hipótesis zombi", "motivo": "nos reímos"},
        {"campo": "opinions", "accion": "quitar", "valor": "vieja", "motivo": "me convenció"},
        {"campo": "interests", "accion": "agregar", "valor": "fractales", "motivo": "surgió"},
        {"campo": "humor_style", "accion": "reemplazar", "valor": "más absurdo", "motivo": "x"},
    ]
    applied = apply_changes(m, changes, agenda)
    assert len(applied) == MAX_CHANGES
    assert m.inside_jokes == ["la hipótesis zombi"] and m.opinions == []
    assert agenda.interests[0].origin == "reflexion" and m.humor_style == ""


# --- reflection end to end -------------------------------------------------

def _reply(prompt):
    return json.dumps({
        "resumen": "Discutimos si las dendritas computan XOR; Usx cambió de opinión.",
        "creencias": [{"quien": "usx", "sujeto": "las dendritas", "relacion": "computan",
                       "objeto": "XOR", "afirma": False, "nivel": "podria_ser",
                       "texto": "ya no creo que computen XOR"}],
        "automodelo": [{"campo": "inside_jokes", "accion": "agregar",
                        "valor": "el XOR dendrítico", "motivo": "broma recurrente"}],
    })


def test_reflection_summarises_extracts_beliefs_versions_and_reverts(tmp_path):
    mem = Memory(":memory:")
    mem.add("s1", "user", "Creo que las dendritas computan XOR")
    mem.add("s1", "assistant", "Podría ser, pero...")
    beliefs = BeliefStore(":memory:")
    beliefs.add("usx", "las dendritas", "computan", "XOR", True)
    model = SelfModel()
    r = Reflector(FakeLLM(_reply), load_constitution(), model, mem, beliefs, tmp_path)
    report, = r.reflect()
    assert ("cambio", "usx", "las dendritas NO computan XOR") in report["beliefs"]
    assert model.inside_jokes == ["el XOR dendrítico"]
    assert mem.search("dendritas", exclude_session="s1")[0].role == "resumen"
    assert [v["version"] for v in r.history.versions()] == [1, 2]
    assert r.reflect() == []  # nothing new to reflect on
    assert r.revert(1) and model.inside_jokes == []
    assert SelfModel.load(tmp_path / "automodelo.json").inside_jokes == []
    assert not r.revert(99)


def test_reflection_survives_bad_json(tmp_path):
    mem = Memory(":memory:")
    mem.add("s1", "user", "hola")
    r = Reflector(FakeLLM(lambda p: "no"), load_constitution(), SelfModel(), mem,
                  BeliefStore(":memory:"), tmp_path)
    assert r.reflect()[0]["error"] == "JSON inválido"
