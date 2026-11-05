"""Interventions from the literature on top of E1 (docs/investigacion/neurosimbolica.md).

C3 (I2, hypothesis search; Wang et al., 2023): propose several natural-language
    hypotheses, translate each into a program, keep the one that explains the examples.
C4 (I3, abstraction library; DreamCoder / LILO): programs that solved earlier tasks are
    kept as named helper functions and offered for reuse in later tasks.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ia.abstraction.solvers import (
    Result, _HEADER, _examples_block, _score_program, extract_code, program_prompt,
    repair_prompt, run_program,
)
from ia.abstraction.tasks import Task
from ia.explore import parse_json_object
from ia.llm import LanguageModel


def _fit(code: str, task: Task) -> int:
    outs = run_program(code, [x for x, _ in task.examples])
    return sum(o == y for (_, y), o in zip(task.examples, outs))


def hypotheses_prompt(task: Task, n: int) -> str:
    return (
        _HEADER + _examples_block(task)
        + f"\nPropose {n} different hypotheses for the hidden rule, each one sentence in "
        "plain English. Make them genuinely different. Reply with only a JSON object: "
        '{"hypotheses": ["...", "..."]}'
    )


def parse_hypotheses(text: str) -> list[str]:
    data = parse_json_object(text)
    if data and isinstance(data.get("hypotheses"), list):
        return [str(h) for h in data["hypotheses"] if str(h).strip()]
    try:
        value = json.loads(text[text.find("["): text.rfind("]") + 1])
        return [str(h) for h in value if str(h).strip()]
    except (json.JSONDecodeError, ValueError):
        return []


def solve_hypotheses(llm: LanguageModel, task: Task, n: int = 3) -> Result:
    hyps = parse_hypotheses(llm.generate(hypotheses_prompt(task, n)))[:n]
    calls, best = 1, ("", -1, None)
    for h in hyps:
        code = extract_code(llm.generate(program_prompt(task) + f"\nImplement this hypothesis: {h}"))
        calls += 1
        fit = _fit(code, task)
        if fit > best[1]:
            best = (code, fit, h)
        if fit == len(task.examples):
            break
    if not hyps:  # fall back to a direct program
        code = extract_code(llm.generate(program_prompt(task)))
        calls += 1
        best = (code, _fit(code, task), None)
    code, fit, chosen = best
    return _score_program(task, code, "C3_hypotheses", calls,
                          {"hypotheses": hyps, "chosen": chosen,
                           "fits_examples": fit == len(task.examples)})


_DEF_F = re.compile(r"\bf\(")


@dataclass
class Library:
    """Verified programs from earlier tasks, reusable as helper functions."""
    functions: list[tuple[str, str]] = field(default_factory=list)
    max_size: int = 20

    def code(self) -> str:
        return "\n\n".join(code for _, code in self.functions)

    def add(self, name: str, program: str) -> None:
        renamed = _DEF_F.sub(f"{name}(", program)
        self.functions = [(n, c) for n, c in self.functions if n != name]
        self.functions.append((name, renamed))
        self.functions = self.functions[-self.max_size:]


def library_prompt(task: Task, library: Library) -> str:
    prompt = program_prompt(task)
    if library.functions:
        prompt += ("\nThese helper functions are already defined and you may call them "
                   "(they solved earlier rules):\n```python\n" + library.code() + "\n```")
    return prompt


def solve_library(llm: LanguageModel, task: Task, library: Library,
                  max_repairs: int = 2) -> Result:
    prefix = library.code()
    full = lambda program: f"{prefix}\n\n{program}" if prefix else program  # noqa: E731
    program = extract_code(llm.generate(library_prompt(task, library)))
    calls = 1
    for _ in range(max_repairs):
        outs = run_program(full(program), [x for x, _ in task.examples])
        failures = [(x, y, o) for (x, y), o in zip(task.examples, outs) if o != y]
        if not failures:
            break
        program = extract_code(llm.generate(
            repair_prompt(task, program, failures)
            + ("\n(The helper functions shown before are still available.)" if prefix else "")))
        calls += 1
    fits = _fit(full(program), task) == len(task.examples)
    used = [n for n, _ in library.functions if re.search(rf"\b{n}\(", program)]
    result = _score_program(task, full(program), "C4_library", calls,
                            {"program": program, "fits_examples": fits,
                             "library_size": len(library.functions), "used": used})
    if fits:
        library.add(f"rule_{task.task_id.replace('-', '_')}", program)
    return result
