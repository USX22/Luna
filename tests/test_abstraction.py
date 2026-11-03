import json
import re

from ia.abstraction.solvers import (
    extract_code, parse_list, run_program, solve_direct, solve_program, solve_verify,
)
from ia.abstraction.tasks import Step, apply_steps, make_suite, make_task
from ia.llm import FakeLLM, strip_thinking


# --- tasks -----------------------------------------------------------------

def test_apply_steps_composes_in_order():
    steps = (Step("map_add", 1), Step("reverse"), Step("take", 2))
    assert apply_steps(steps, [1, 2, 3]) == [4, 3]


def test_make_task_is_reproducible():
    a, b = make_task(7, 2), make_task(7, 2)
    assert a.rule == b.rule and a.examples == b.examples


def test_reference_program_matches_semantics():
    for task in make_suite(5):
        outs = run_program(task.source, [x for x, _ in task.examples + task.queries_ood])
        assert outs == [y for _, y in task.examples + task.queries_ood]


def test_tasks_are_not_identity_and_ood_is_longer():
    for task in make_suite(5):
        assert any(x != y for x, y in task.examples)
        assert min(len(x) for x, _ in task.queries_ood) > max(len(x) for x, _ in task.examples)


# --- parsing and execution -------------------------------------------------

def test_parse_list_takes_last_valid_list():
    assert parse_list("Rule [a] gives [1, 2] so answer: [3, 4]") == [3, 4]
    assert parse_list("no list here") is None


def test_extract_code_and_strip_thinking():
    text = "<think>hmm</think>Sure:\n```python\ndef f(xs):\n    return xs\n```"
    assert extract_code(strip_thinking(text)) == "def f(xs):\n    return xs"


def test_run_program_isolates_errors_and_timeouts():
    assert run_program("def f(xs): return 1/0", [[1]]) == [None]
    assert run_program("syntax error(", [[1], [2]]) == [None, None]
    assert run_program("def f(xs):\n    while True: pass", [[1]], timeout=1) == [None]


# --- solvers with fake models ----------------------------------------------

def _oracle_llm(task):
    """Fake model that knows the true rule."""
    def respond(prompt):
        if "Write a Python function" in prompt:
            return f"```python\n{task.source}```"
        query = json.loads(re.search(r"Apply the same rule to: (\[.*?\])", prompt).group(1))
        return json.dumps(apply_steps(task.steps, query))
    return FakeLLM(respond)


def test_oracle_scores_perfectly_in_all_conditions():
    task = make_task(3, 3)
    for solve in (solve_direct, solve_program, solve_verify):
        r = solve(_oracle_llm(task), task)
        assert (r.acc_in, r.acc_ood) == (1.0, 1.0), r.condition


def test_verify_repairs_a_wrong_program():
    task = make_task(1, 2)
    answers = iter(["```python\ndef f(xs):\n    return xs\n```", f"```python\n{task.source}```"])
    llm = FakeLLM(lambda p: next(answers))
    r = solve_verify(llm, task)
    assert r.extra["repairs"] == 1 and r.extra["fits_examples"]
    assert r.acc_ood == 1.0
    assert "fails on these examples" in llm.prompts[1]


def test_wrong_program_scores_zero_without_verification():
    task = make_task(1, 2)
    r = solve_program(FakeLLM(lambda p: "```python\ndef f(xs):\n    return []\n```"), task)
    assert r.acc_in < 1.0
