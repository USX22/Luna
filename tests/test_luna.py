from ia.llm import FakeLLM
from ia.luna import Luna
from ia.memory import Memory
from ia.persona import SelfModel, load_constitution, render_system_prompt


# --- personality -----------------------------------------------------------

def test_constitution_loads_with_observable_behaviours():
    c = load_constitution()
    assert c.name == "Luna"
    ids = {p.id for p in c.principles}
    assert {"lealtad", "honestidad", "no_complacencia", "reciprocidad", "autonomia"} <= ids
    for p in c.principles:
        assert p.do and p.dont, f"{p.id} needs observable do/dont behaviours"


def test_self_model_seeds_on_first_run_and_persists(tmp_path):
    path = tmp_path / "automodelo.json"
    s = SelfModel.load(path)
    assert path.exists() and s.interests
    s.inside_jokes.append("la hipótesis zombi")
    s.save(path)
    assert "la hipótesis zombi" in SelfModel.load(path).inside_jokes


def test_system_prompt_contains_principles_and_self_model():
    c = load_constitution()
    prompt = render_system_prompt(c, SelfModel(interests=["topología"], inside_jokes=["X"]))
    for p in c.principles:
        assert p.name in prompt
    assert "Inventar datos" in prompt and "topología" in prompt and "X" in prompt


# --- memory ----------------------------------------------------------------

def test_memory_search_is_accent_insensitive_and_excludes_session():
    m = Memory(":memory:")
    m.add("s1", "user", "Hablemos de la hipótesis del espacio de trabajo global")
    m.add("s2", "user", "hipotesis nueva sobre dendritas")
    hits = m.search("hipotesis", exclude_session="s2")
    assert [h.session for h in hits] == ["s1"]


def test_memory_search_handles_odd_input_and_forget():
    m = Memory(":memory:")
    eid = m.add("s1", "user", "recuerda las dendritas")
    assert m.search('"; DROP TABLE episodes; --') == []
    assert m.search("??") == []
    assert m.forget(eid) and not m.forget(eid)
    assert m.search("dendritas") == [] and m.count() == 0


# --- core ------------------------------------------------------------------

def _luna(memory, session, respond=lambda t: "ok"):
    llm = FakeLLM(respond)
    return Luna(llm, load_constitution(), SelfModel(), memory, session=session), llm


def test_reply_stores_turns_and_keeps_conversation_context():
    m = Memory(":memory:")
    luna, llm = _luna(m, "s1", lambda t: f"eco: {t}")
    luna.reply("hola")
    luna.reply("¿qué dije?")
    roles = [msg["role"] for msg in llm.chats[-1]]
    assert roles == ["system", "user", "assistant", "user"]
    assert m.count() == 4


def test_memories_from_previous_sessions_are_recalled():
    m = Memory(":memory:")
    old, _ = _luna(m, "old")
    old.reply("Mi hipótesis es que las dendritas computan XOR")
    new, llm = _luna(m, "new")
    new.reply("¿Te acuerdas de mi hipótesis sobre dendritas?")
    system = llm.chats[-1][0]["content"]
    assert "computan XOR" in system and "nunca inventes recuerdos" in system
