"""E1: does the language model abstract, or interpolate examples?

Usage (Ollama must be running):
    python experiments/e1_abstraction.py --model qwen3.5:4b --n 10
    OLLAMA_HOST=http://192.168.1.50:11434 python experiments/e1_abstraction.py --model qwen3.5:9b

Results go to results/e1/<model>_<timestamp>.jsonl plus a summary table.
See docs/investigacion/neurosimbolica.md for hypotheses and design.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from ia.abstraction.solvers import SOLVERS
from ia.abstraction.tasks import make_suite
from ia.llm import OllamaLLM


def summarize(rows: list[dict]) -> str:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["condition"], r["depth"])].append(r)
    lines = [f"{'condition':<12}{'depth':>6}{'n':>5}{'acc_in':>9}{'acc_ood':>9}"]
    for (cond, depth), rs in sorted(groups.items()):
        a_in = sum(r["acc_in"] for r in rs) / len(rs)
        a_ood = sum(r["acc_ood"] for r in rs) / len(rs)
        lines.append(f"{cond:<12}{depth:>6}{len(rs):>5}{a_in:>9.2f}{a_ood:>9.2f}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True, help="Ollama model name")
    ap.add_argument("--n", type=int, default=10, help="tasks per depth")
    ap.add_argument("--depths", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--conditions", nargs="+", default=list(SOLVERS), choices=list(SOLVERS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e1")
    args = ap.parse_args()

    llm = OllamaLLM(args.model)
    tasks = make_suite(args.n, tuple(args.depths), args.seed)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.model.replace(':', '_').replace('/', '_')}_{int(time.time())}.jsonl"

    rows = []
    with out_path.open("w") as fh:
        for i, task in enumerate(tasks, 1):
            for cond in args.conditions:
                result = SOLVERS[cond](llm, task).to_dict()
                result.update(model=args.model, seed=args.seed)
                rows.append(result)
                fh.write(json.dumps(result) + "\n")
                fh.flush()
                print(f"[{i}/{len(tasks)}] {task.task_id} {cond}: "
                      f"in={result['acc_in']:.2f} ood={result['acc_ood']:.2f}  ({task.rule})")

    print("\n" + summarize(rows))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
