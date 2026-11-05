import json

from ia.abstraction.interventions import (
    Library, parse_hypotheses, solve_hypotheses, solve_library,
)
from ia.abstraction.tasks import make_task
from ia.llm import FakeLLM


def test_parse_hypotheses_formats():
    assert parse_hypotheses('{"hypotheses": ["a", "b"]}') == ["a", "b"]
    assert parse_hypotheses('Sure: ["x", "y"]') == ["x", "y"]
    assert parse_hypotheses("nothing") == []


def test_hypothesis_search_picks_the_hypothesis_that_fits():
    task = make_task(1, 2)

    def respond(p):
        if "Propose 3 different hypotheses" in p:
            return json.dumps({"hypotheses": ["identity", "the true rule", "empty"]})
        if "Implement this hypothesis: the true rule" in p:
            return f"```python\n{task.source}```"
        if "Implement this hypothesis: identity" in p:
            return "```python\ndef f(xs):\n    return xs\n```"
        return "```python\ndef f(xs):\n    return []\n```"

    r = solve_hypotheses(FakeLLM(respond), task)
    assert r.extra["chosen"] == "the true rule" and r.acc_ood == 1.0
    assert r.n_calls == 3  # stops at the first hypothesis that fits


def test_library_renames_and_caps():
    lib = Library(max_size=2)
    lib.add("rule_a", "def f(xs):\n    return f(xs[1:]) if xs else xs")
    assert "def rule_a(xs)" in lib.code() and "return rule_a(xs[1:])" in lib.code()
    lib.add("rule_b", "def f(xs):\n    return xs")
    lib.add("rule_c", "def f(xs):\n    return xs")
    assert [n for n, _ in lib.functions] == ["rule_b", "rule_c"]


def test_library_grows_and_later_programs_can_call_it():
    first = make_task(0, 1)
    lib = Library()
    r1 = solve_library(FakeLLM(lambda p: f"```python\n{first.source}```"), first, lib)
    assert r1.extra["fits_examples"] and lib.functions[0][0] == "rule_d1_s0"

    second = make_task(5, 2)
    name = lib.functions[0][0]
    calls_helper = (f"```python\ndef f(xs):\n    _ = {name}(xs)\n"
                    + second.source.split("\n", 1)[1] + "```")
    llm = FakeLLM(lambda p: calls_helper)
    r2 = solve_library(llm, second, lib)
    assert "already defined" in llm.prompts[0] and name in llm.prompts[0]
    assert r2.extra["used"] == [name] and r2.acc_ood == 1.0
    assert len(lib.functions) == 2
