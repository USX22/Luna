"""Three ways of solving a hidden-rule task.

C0 direct    : the language model predicts each output list (neural only).
C1 program   : the model writes f(xs); outputs come from executing it (symbolic).
C2 verify    : like C1, but the program is checked on the examples and the model
               gets the failures back to repair it (hypothesis -> test -> revise).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field

from ia.abstraction.tasks import Task
from ia.llm import LanguageModel

_HEADER = (
    "There is a hidden rule that transforms a list of integers into another list.\n"
    "Examples:\n"
)


def _examples_block(task: Task) -> str:
    return "".join(f"{json.dumps(x)} -> {json.dumps(y)}\n" for x, y in task.examples)


def direct_prompt(task: Task, query: list[int]) -> str:
    return (
        _HEADER + _examples_block(task)
        + f"\nApply the same rule to: {json.dumps(query)}\n"
        "Answer with only the output list as JSON, nothing else."
    )


def program_prompt(task: Task) -> str:
    return (
        _HEADER + _examples_block(task)
        + "\nWrite a Python function `f(xs)` that implements the rule for any list.\n"
        "Reply with only the code in a ```python block."
    )


def repair_prompt(task: Task, code: str, failures: list[tuple[list, list, object]]) -> str:
    lines = "".join(
        f"input {json.dumps(x)}: expected {json.dumps(y)}, got {json.dumps(got)}\n"
        for x, y, got in failures
    )
    return (
        program_prompt(task)
        + f"\n\nYour previous attempt:\n```python\n{code}\n```\n"
        f"It fails on these examples:\n{lines}"
        "Think about which rule explains all examples, then reply with the corrected "
        "code only, in a ```python block."
    )


_LIST_RE = re.compile(r"\[[^\[\]]*\]")
_CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def parse_list(text: str) -> list[int] | None:
    """Take the last flat JSON list of integers in the text."""
    for candidate in reversed(_LIST_RE.findall(text)):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and all(isinstance(v, int) for v in value):
            return value
    return None


def extract_code(text: str) -> str:
    blocks = _CODE_RE.findall(text)
    return (blocks[-1] if blocks else text).strip()


_RUNNER = r"""
import json, sys
data = json.load(sys.stdin)
ns = {}
results = []
try:
    exec(data["code"], ns)
    f = ns["f"]
except Exception:
    print(json.dumps([None] * len(data["inputs"])))
    sys.exit(0)
for xs in data["inputs"]:
    try:
        out = f(list(xs))
        out = [int(v) for v in out]
    except Exception:
        out = None
    results.append(out)
print(json.dumps(results))
"""


def run_program(code: str, inputs: list[list[int]], timeout: float = 5.0) -> list:
    """Execute model-written code in a separate Python process with a timeout.

    This isolates crashes and infinite loops, but it is NOT a security sandbox:
    only run it with models you trust on your own machine.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", _RUNNER],
            input=json.dumps({"code": code, "inputs": inputs}),
            capture_output=True, text=True, timeout=timeout,
        )
        return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return [None] * len(inputs)


@dataclass
class Result:
    task_id: str
    condition: str
    depth: int
    rule: str
    acc_in: float
    acc_ood: float
    n_calls: int
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _accuracy(preds: list, pairs: list[tuple[list, list]]) -> float:
    return sum(p == y for p, (_, y) in zip(preds, pairs)) / len(pairs)


def solve_direct(llm: LanguageModel, task: Task) -> Result:
    def predict(pairs):
        return [parse_list(llm.generate(direct_prompt(task, x))) for x, _ in pairs]

    p_in, p_ood = predict(task.queries_in), predict(task.queries_ood)
    return Result(task.task_id, "C0_direct", task.depth, task.rule,
                  _accuracy(p_in, task.queries_in), _accuracy(p_ood, task.queries_ood),
                  len(task.queries_in) + len(task.queries_ood))


def _score_program(task: Task, code: str, condition: str, n_calls: int, extra: dict) -> Result:
    inputs = [x for x, _ in task.queries_in + task.queries_ood]
    preds = run_program(code, inputs)
    n = len(task.queries_in)
    extra = {**extra, "code": code}
    return Result(task.task_id, condition, task.depth, task.rule,
                  _accuracy(preds[:n], task.queries_in), _accuracy(preds[n:], task.queries_ood),
                  n_calls, extra)


def solve_program(llm: LanguageModel, task: Task) -> Result:
    code = extract_code(llm.generate(program_prompt(task)))
    return _score_program(task, code, "C1_program", 1, {})


def solve_verify(llm: LanguageModel, task: Task, max_repairs: int = 2) -> Result:
    code = extract_code(llm.generate(program_prompt(task)))
    calls, repairs = 1, 0
    for _ in range(max_repairs):
        outs = run_program(code, [x for x, _ in task.examples])
        failures = [(x, y, o) for (x, y), o in zip(task.examples, outs) if o != y]
        if not failures:
            break
        code = extract_code(llm.generate(repair_prompt(task, code, failures)))
        calls += 1
        repairs += 1
    outs = run_program(code, [x for x, _ in task.examples])
    fits = all(o == y for (_, y), o in zip(task.examples, outs))
    return _score_program(task, code, "C2_verify", calls,
                          {"repairs": repairs, "fits_examples": fits})


SOLVERS = {"C0": solve_direct, "C1": solve_program, "C2": solve_verify}
