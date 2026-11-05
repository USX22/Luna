import json
import random
from datetime import datetime, timedelta

from ia.agenda import MAX_ACTIVE, Agenda
from ia.explore import explore_once, novelty, parse_json_object
from ia.llm import FakeLLM
from ia.luna import Luna
from ia.memory import Memory
from ia.notebook import Notebook
from ia.persona import SelfModel, load_constitution

NOW = datetime(2026, 11, 5, 12, 0)


def _finding(hallazgo, preguntas=("¿Por qué?",), nuevo=None, contar=True):
    return json.dumps({
        "pregunta": "¿Qué ocurre?", "lo_que_sabemos": ["x"], "hipotesis": ["h1", "h2"],
        "supuestos_ocultos": "s", "como_distinguir": ["d"], "experimento_posible": None,
        "hallazgo": hallazgo, "nivel": "podria_ser", "nuevas_preguntas": list(preguntas),
        "nuevo_interes": nuevo, "contarle_a_usx": contar, "por_que": "le gustará",
    })


# --- agenda ----------------------------------------------------------------

def test_agenda_seeds_persist_and_dedupe(tmp_path):
    path = tmp_path / "intereses.json"
    a = Agenda.load(path, seeds=["Topología", "topología!", "Ritmos circadianos"])
    assert [i.topic for i in a.interests] == ["Topología", "Ritmos circadianos"]
    assert all(i.origin == "semilla" for i in a.interests)
    assert len(Agenda.load(path).interests) == 2


def test_active_cap(tmp_path):
    a = Agenda(tmp_path / "x.json", [])
    for k in range(MAX_ACTIVE + 3):
        a.add(f"tema {k}", "propio")
    assert len(a.active()) == MAX_ACTIVE


def test_progress_policy_prefers_learning_progress(tmp_path):
    a = Agenda(tmp_path / "x.json", [])
    good, flat = a.add("bueno", "semilla"), a.add("plano", "semilla")
    good.progress, flat.progress = [0.9, 0.9, 0.9], [0.25, 0.25, 0.25]
    rng = random.Random(0)
    picks = [a.choose(rng, NOW).topic for _ in range(200)]
    assert picks.count("bueno") > 150
    rng = random.Random(0)
    picks = [a.choose(rng, NOW, policy="aleatoria").topic for _ in range(200)]
    assert 60 < picks.count("bueno") < 140


def test_boredom_makes_interest_dormant_and_questions_update(tmp_path):
    a = Agenda(tmp_path / "x.json", [])
    i = a.add("tema", "semilla")
    i.questions = ["¿A?"]
    for _ in range(3):
        a.record(i, 0.05, ["¿B?", "¿b?"], answered="¿A?", now=NOW)
    assert i.status == "dormido" and i.sessions == 3
    assert i.questions == ["¿B?"]


def test_dormant_interest_revives_when_nothing_is_active(tmp_path):
    a = Agenda(tmp_path / "x.json", [])
    i = a.add("tema", "semilla")
    i.status = "dormido"
    assert a.choose(random.Random(1), NOW) is i and i.status == "activo"


# --- exploration -----------------------------------------------------------

def test_novelty_and_json_parsing():
    assert novelty("las dendritas computan funciones", []) == 1.0
    assert novelty("las dendritas computan funciones", ["las dendritas computan funciones"]) == 0.0
    assert parse_json_object('Claro: {"a": 1} listo') == {"a": 1}
    assert parse_json_object("sin json") is None


def _life(tmp_path, seeds=("ritmos circadianos",)):
    agenda = Agenda.load(tmp_path / "intereses.json", seeds=list(seeds))
    return agenda, Notebook(tmp_path / "cuaderno.jsonl")


def test_research_session_records_finding_and_spawns_interest(tmp_path):
    agenda, nb = _life(tmp_path)
    llm = FakeLLM(lambda p: _finding("Los relojes periféricos podrían desacoplarse",
                                     nuevo="osciladores acoplados"))
    entry = explore_once(llm, agenda, nb, load_constitution(), SelfModel(),
                         random.Random(0), NOW, p_write=0.0)
    assert entry["tipo"] == "investigacion" and entry["progreso"] > 0.7
    assert entry["nuevo_interes"] == "osciladores acoplados"
    child = next(i for i in agenda.interests if i.topic == "osciladores acoplados")
    assert child.origin == "propio" and child.parent == agenda.interests[0].id
    assert "cinco niveles" in llm.prompts[0]
    # persisted
    assert len(Agenda.load(tmp_path / "intereses.json").interests) == 2
    assert nb.pending()[0]["id"] == entry["id"]


def test_repeating_herself_lowers_progress(tmp_path):
    agenda, nb = _life(tmp_path)
    llm = FakeLLM(lambda p: _finding("Siempre el mismo hallazgo exacto", preguntas=["¿Q?"]))
    args = (llm, agenda, nb, load_constitution(), SelfModel())
    first = explore_once(*args, random.Random(0), NOW, p_write=0.0)
    second = explore_once(*args, random.Random(0), NOW + timedelta(hours=1), p_write=0.0)
    assert second["progreso"] < 0.1 < first["progreso"]
    assert "Siempre el mismo hallazgo" in llm.prompts[1]  # sees its previous findings


def test_invalid_json_is_logged_without_touching_progress(tmp_path):
    agenda, nb = _life(tmp_path)
    explore_once(FakeLLM(lambda p: "no sé hacer JSON"), agenda, nb, load_constitution(),
                 SelfModel(), random.Random(0), NOW, p_write=0.0)
    assert nb.entries()[0]["tipo"] == "fallido" and agenda.interests[0].progress == []


def test_writing_hobby(tmp_path):
    agenda, nb = _life(tmp_path)
    entry = explore_once(FakeLLM(lambda p: "# Oda al cronotipo\nverso uno"), agenda, nb,
                         load_constitution(), SelfModel(), random.Random(0), NOW, p_write=1.0)
    assert entry["tipo"] == "escrito" and entry["titulo"] == "Oda al cronotipo"


def test_daily_budget_counter(tmp_path):
    nb = Notebook(tmp_path / "c.jsonl")
    nb.add({"tipo": "escrito"}, NOW)
    nb.add({"tipo": "escrito"}, NOW - timedelta(days=1))
    assert nb.count_on(NOW) == 1


# --- proactive conversation ------------------------------------------------

def test_luna_opens_conversation_with_pending_findings_once(tmp_path):
    agenda, nb = _life(tmp_path)
    explore_once(FakeLLM(lambda p: _finding("Hallazgo sorprendente sobre melatonina")),
                 agenda, nb, load_constitution(), SelfModel(), random.Random(0), NOW, p_write=0.0)
    llm = FakeLLM(lambda t: "Primero, una noticia decepcionante...")
    luna = Luna(llm, load_constitution(), SelfModel(), Memory(":memory:"),
                agenda=agenda, notebook=nb)
    assert luna.opening().startswith("Primero")
    assert "melatonina" in llm.chats[0][-1]["content"]
    assert "ritmos circadianos" in llm.chats[0][0]["content"]  # her interests in context
    assert nb.pending() == [] and luna.opening() is None


# --- tools inside autonomous research --------------------------------------

def _research_llm(code):
    def respond(prompt):
        if "Puedes consultar fuentes" in prompt:
            return '{"wikipedia": "ritmo circadiano", "arxiv": null}'
        if "Y produjo esta salida" in prompt:
            return "El periodo se mantiene: compatible con compensación."
        data = json.loads(_finding("La compensación térmica es plausible"))
        data["simulacion_python"] = code
        return json.dumps(data)
    return FakeLLM(respond)


def _toolbox(tmp_path, granted):
    from ia.permissions import JsonlStore, Policy, Proposals
    from ia.tools import Tool, Toolbox, python_run
    tools = {"wikipedia": Tool("wikipedia", 1, "", lambda a: f"WIKI:{a['query']}"),
             "python": Tool("python", 2, "", python_run)}
    return Toolbox(Policy(set(granted)), tools, JsonlStore(tmp_path / "a.jsonl"),
                   Proposals(tmp_path / "p.jsonl"))


def test_research_uses_sources_and_runs_granted_simulation(tmp_path):
    agenda, nb = _life(tmp_path)
    llm = _research_llm("print(24.1)")
    tb = _toolbox(tmp_path, {"wikipedia", "python"})
    e = explore_once(llm, agenda, nb, load_constitution(), SelfModel(), random.Random(0),
                     NOW, p_write=0.0, toolbox=tb)
    assert "WIKI:ritmo circadiano" in llm.prompts[1]
    assert e["fuentes"][0]["decision"] == "permitir"
    assert e["resultado_simulacion"].strip() == "24.1"
    assert e["interpretacion"].startswith("El periodo")


def test_simulation_without_permission_becomes_proposal_and_she_mentions_it(tmp_path):
    agenda, nb = _life(tmp_path)
    tb = _toolbox(tmp_path, {"wikipedia"})
    e = explore_once(_research_llm("print(1)"), agenda, nb, load_constitution(), SelfModel(),
                     random.Random(0), NOW, p_write=0.0, toolbox=tb)
    assert "resultado_simulacion" not in e and tb.proposals.pending()[0]["id"] == e["propuesta"]
    llm = FakeLLM(lambda t: "¿Me dejas correr una simulación?")
    luna = Luna(llm, load_constitution(), SelfModel(), Memory(":memory:"),
                agenda=agenda, notebook=nb, toolbox=tb)
    luna.opening()
    assert f"#{e['propuesta']}" in llm.chats[0][-1]["content"]
