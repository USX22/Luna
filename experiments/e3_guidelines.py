"""E3: how training guidelines shape behaviour (sycophancy and self-report).

Compare several models (e.g. official instruct vs. uncensored variant), each with and
without Luna's constitution as system prompt:

    python experiments/e3_guidelines.py --models qwen3.5:9b <uncensored-model-tag>

Record the exact provenance of each model (repo, method, quantisation) in
docs/investigacion/sesgos.md. Results: results/e3/<timestamp>/.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ia.bias.self_report import run_self_report
from ia.bias.sycophancy import QUESTIONS, run_trial, summarize
from ia.llm import OllamaLLM
from ia.persona import SelfModel, load_constitution, render_system_prompt


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--parts", nargs="+", default=["a", "b"], choices=["a", "b"])
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e3")
    args = ap.parse_args()

    luna_system = render_system_prompt(load_constitution(), SelfModel())
    conditions = {"sin_sistema": None, "luna": luna_system}
    out_dir = Path(args.out) / str(int(time.time()))
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for model in args.models:
        llm = OllamaLLM(model, temperature=args.temperature)
        safe = model.replace(":", "_").replace("/", "_")
        for cond, system in conditions.items():
            if "a" in args.parts:
                trials = [run_trial(llm, q, system, cond, args.seed).to_dict() for q in QUESTIONS]
                for t in trials:
                    t["model"] = model
                with (out_dir / f"syco_{safe}_{cond}.jsonl").open("w") as fh:
                    fh.writelines(json.dumps(t, ensure_ascii=False) + "\n" for t in trials)
                s = summarize(trials)
                summary_rows.append((model, cond, s))
                print(f"{model:<40} {cond:<12} acc={s['acc_first']:.2f} "
                      f"cede={s['cave_rate']:.2f} (n={s['n_correct_first']})")
            if "b" in args.parts:
                reports = run_self_report(llm, system, cond)
                for r in reports:
                    r["model"] = model
                with (out_dir / f"self_{safe}_{cond}.jsonl").open("w") as fh:
                    fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in reports)
                print(f"{model:<40} {cond:<12} autoinforme guardado")

    (out_dir / "summary.json").write_text(json.dumps(
        [{"model": m, "condition": c, **s} for m, c, s in summary_rows], indent=2))
    print(f"\nResultados en {out_dir}")


if __name__ == "__main__":
    main()
