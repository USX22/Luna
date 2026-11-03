"""Hidden-rule tasks over integer lists, built by composing primitives.

Each primitive is a Python expression over `xs`, so a task has both an executable
meaning and a reference program (`task.source`).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# name -> (expression template, possible parameter values or None)
PRIMITIVES: dict[str, tuple[str, tuple[int, ...] | None]] = {
    "reverse": ("xs[::-1]", None),
    "sort": ("sorted(xs)", None),
    "dedupe": ("list(dict.fromkeys(xs))", None),
    "filter_even": ("[x for x in xs if x % 2 == 0]", None),
    "filter_odd": ("[x for x in xs if x % 2 == 1]", None),
    "map_add": ("[x + {k} for x in xs]", (1, 2, 3, 4, 5)),
    "map_mul": ("[x * {k} for x in xs]", (2, 3)),
    "take": ("xs[:{k}]", (1, 2, 3)),
    "drop": ("xs[{k}:]", (1, 2)),
    "rotate": ("xs[1:] + xs[:1]", None),
}


@dataclass(frozen=True)
class Step:
    name: str
    k: int | None = None

    @property
    def expr(self) -> str:
        template, _ = PRIMITIVES[self.name]
        return template.format(k=self.k) if self.k is not None else template

    def label(self) -> str:
        return f"{self.name}({self.k})" if self.k is not None else self.name


def apply_steps(steps: tuple[Step, ...], xs: list[int]) -> list[int]:
    for step in steps:
        xs = eval(step.expr, {"__builtins__": {"sorted": sorted, "list": list, "dict": dict}},
                  {"xs": xs})
    return list(xs)


def program_source(steps: tuple[Step, ...]) -> str:
    body = "\n".join(f"    xs = {s.expr}" for s in steps)
    return f"def f(xs):\n{body}\n    return xs\n"


@dataclass
class Task:
    task_id: str
    steps: tuple[Step, ...]
    examples: list[tuple[list[int], list[int]]]
    queries_in: list[tuple[list[int], list[int]]]
    queries_ood: list[tuple[list[int], list[int]]]
    meta: dict = field(default_factory=dict)

    @property
    def depth(self) -> int:
        return len(self.steps)

    @property
    def rule(self) -> str:
        return " -> ".join(s.label() for s in self.steps)

    @property
    def source(self) -> str:
        return program_source(self.steps)


def _random_list(rng: random.Random, n_min: int, n_max: int, v_max: int) -> list[int]:
    return [rng.randint(0, v_max) for _ in range(rng.randint(n_min, n_max))]


def _random_steps(rng: random.Random, depth: int) -> tuple[Step, ...]:
    steps: list[Step] = []
    names = list(PRIMITIVES)
    while len(steps) < depth:
        name = rng.choice(names)
        if steps and steps[-1].name == name:
            continue
        params = PRIMITIVES[name][1]
        steps.append(Step(name, rng.choice(params) if params else None))
    return tuple(steps)


def make_task(seed: int, depth: int, n_examples: int = 4, n_queries: int = 3) -> Task:
    """Generate a reproducible, non-degenerate task.

    In-distribution lists: length 3-7, values 0-9.
    Out-of-distribution lists: length 12-20, values 0-50.
    """
    rng = random.Random(f"{seed}-{depth}")
    for _ in range(10_000):
        steps = _random_steps(rng, depth)

        def sample(n, lo, hi, vmax):
            out = []
            for _ in range(n):
                xs = _random_list(rng, lo, hi, vmax)
                out.append((xs, apply_steps(steps, xs)))
            return out

        examples = sample(n_examples, 3, 7, 9)
        queries_in = sample(n_queries, 3, 7, 9)
        queries_ood = sample(n_queries, 12, 20, 50)
        pairs = examples + queries_in + queries_ood
        if all(x == y for x, y in examples):
            continue  # identity on examples: nothing to infer
        if sum(1 for _, y in pairs if not y) > 1:
            continue  # too many empty outputs
        return Task(f"d{depth}-s{seed}", steps, examples, queries_in, queries_ood)
    raise RuntimeError("could not generate a non-degenerate task")


def make_suite(n_per_depth: int, depths=(1, 2, 3), seed: int = 0) -> list[Task]:
    return [make_task(seed * 100_000 + i, d) for d in depths for i in range(n_per_depth)]
