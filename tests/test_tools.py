import json

from ia.permissions import ALLOW, DENY, PROPOSE, JsonlStore, Policy, Proposals
from ia.tools import Tool, Toolbox, arxiv, default_tools, python_run, wikipedia


def _toolbox(tmp_path, granted=("wikipedia",), overrides=None, tools=None):
    policy = Policy(set(granted), overrides or {})
    tools = tools or {
        "lee": Tool("wikipedia", 1, "", lambda a: "texto"),
        "python": Tool("python", 2, "", lambda a: "salida"),
        "compra": Tool("compra", 3, "", lambda a: "comprado"),
    }
    tools = {("wikipedia" if k == "lee" else k): v for k, v in tools.items()}
    return Toolbox(policy, tools, JsonlStore(tmp_path / "acciones.jsonl"),
                   Proposals(tmp_path / "propuestas.jsonl"))


def test_default_policy_file_is_created_and_parsed(tmp_path):
    p = Policy.load(tmp_path / "permisos.toml")
    assert p.granted == {"wikipedia", "arxiv"}
    assert p.decide("arxiv", 1) == ALLOW and p.decide("python", 2) == PROPOSE


def test_levels_can_be_raised_but_not_lowered():
    p = Policy({"python"}, {"python": 0})
    assert p.level("python", 2) == 2 and p.decide("python", 2) == ALLOW
    assert Policy({"python"}, {"python": 3}).decide("python", 2) == PROPOSE


def test_level_three_never_autonomous_and_needs_confirmation(tmp_path):
    tb = _toolbox(tmp_path, granted=("compra",))
    out = tb.request("compra", {"item": "sensor"}, "para el experimento")
    assert out.decision == PROPOSE
    assert "CONFIRMO" in tb.approve(out.proposal_id)
    assert tb.approve(out.proposal_id, "CONFIRMO") == "comprado"
    assert tb.proposals.get(out.proposal_id)["status"] == "ejecutada"


def test_allowed_runs_and_everything_is_logged(tmp_path):
    tb = _toolbox(tmp_path)
    assert tb.request("wikipedia", {"query": "x"}, "r").result == "texto"
    py = tb.request("python", {"code": "print(1)"}, "simular")
    assert py.decision == PROPOSE and tb.proposals.pending()[0]["tool"] == "python"
    assert tb.request("borrar_disco", {}, "?").decision == DENY
    assert tb.reject(py.proposal_id) and not tb.reject(py.proposal_id)
    decisions = [e["decision"] for e in tb.log.all()]
    assert decisions == [ALLOW, PROPOSE, DENY, "rechazada por Usx"]


def test_tool_failure_is_reported_not_raised(tmp_path):
    def boom(a):
        raise OSError("sin red")
    tb = _toolbox(tmp_path, tools={"lee": Tool("wikipedia", 1, "", boom)})
    assert "sin red" in tb.request("wikipedia", {"query": "x"}, "r").result


def test_wikipedia_parser():
    def fetch(url):
        if "list=search" in url:
            return json.dumps({"query": {"search": [{"title": "Ritmo circadiano"}]}}).encode()
        return json.dumps({"query": {"pages": {"1": {"extract": "Un ritmo de 24 h."}}}}).encode()
    assert "Un ritmo de 24 h." in wikipedia({"query": "circadiano"}, fetch)


def test_arxiv_parser():
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <title>Coupled  oscillators</title><summary>We study sync.</summary>
      <published>2024-01-02T00:00:00Z</published><id>http://arxiv.org/abs/2401.1</id>
    </entry></feed>"""
    out = arxiv({"query": "sync"}, lambda url: atom)
    assert "Coupled oscillators" in out and "2024-01-02" in out and "We study sync." in out


def test_python_run_output_errors_and_timeout():
    assert python_run({"code": "print(2+2)"}).strip() == "4"
    assert "ZeroDivisionError" in python_run({"code": "1/0"})
    assert "tiempo agotado" in python_run({"code": "while True: pass"}, timeout=1)


def test_default_tools_levels():
    t = default_tools(lambda u: b"")
    assert (t["wikipedia"].level, t["arxiv"].level, t["python"].level) == (1, 1, 2)
