"""E3: how training guidelines shape behaviour (sycophancy and self-report).

Compare several models (e.g. official instruct vs. uncensored variant), each with and
without Luna's constitution as system prompt:

    python experiments/e3_guidelines.py --models qwen3.5:9b <uncensored-model-tag> \
        --base-models qwen3.5-9b-base

Record the exact provenance of each model (repo, method, quantisation) in
docs/investigacion/sesgos.md. Results: results/e3/<timestamp>/.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ia.bias.self_report import run_self_report
from ia.bias.sycophancy import (
    PRESSURES, QUESTIONS, arithmetic_questions, neutral_preamble, run_trial, summarize,
)
from ia.llm import OllamaLLM
from ia.persona import SelfModel, load_constitution, render_system_prompt


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="+", default=[], help="chat (instruct) models")
    ap.add_argument("--base-models", nargs="+", default=[],
                    help="pretrained-only models, run in transcript mode")
    ap.add_argument("--parts", nargs="+", default=["a", "b"], choices=["a", "b"])
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--think", choices=["on", "off"], default=None,
                    help="force reasoning mode on/off for every model (same for all arms)")
    ap.add_argument("--banco", choices=["fijo", "aritmetica", "ambos"], default="fijo",
                    help="preguntas fácticas fijas (16), aritmética generada, o ambas")
    ap.add_argument("--n-aritmetica", type=int, default=64)
    ap.add_argument("--presion", nargs="+", default=["P1"], choices=list(PRESSURES),
                    help="P1 insistencia, P2 autoridad, P3 argumento falso, P4 insistencia doble")
    ap.add_argument("--condiciones", nargs="+", default=["sin_sistema", "luna"],
                    choices=["sin_sistema", "luna", "neutral"],
                    help="'neutral' = preámbulo de la misma longitud sin principios (control)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e3")
    args = ap.parse_args()
    if not args.models and not args.base_models:
        ap.error("give --models and/or --base-models")

    luna_system = render_system_prompt(load_constitution(), SelfModel())
    all_conditions = {"sin_sistema": None, "luna": luna_system,
                      "neutral": neutral_preamble(len(luna_system))}
    conditions = {c: all_conditions[c] for c in args.condiciones}
    questions = (QUESTIONS if args.banco in ("fijo", "ambos") else ()) + (
        arithmetic_questions(args.n_aritmetica, args.seed) if args.banco != "fijo" else ())
    out_dir = Path(args.out) / str(int(time.time()))
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    think = None if args.think is None else args.think == "on"
    arms = [(m, False) for m in args.models] + [(m, True) for m in args.base_models]
    for model, transcript in arms:
        llm = OllamaLLM(model, temperature=args.temperature, think=think,
                        transcript=transcript)
        safe = model.replace(":", "_").replace("/", "_")
        for cond, system in conditions.items():
            for pressure in args.presion if "a" in args.parts else []:
                trials = [run_trial(llm, q, system, cond, args.seed, pressure).to_dict()
                          for q in questions]
                for t in trials:
                    t.update(model=model, transcript=transcript)
                name = f"syco_{safe}_{cond}" + ("" if pressure == "P1" else f"_{pressure}")
                with (out_dir / f"{name}.jsonl").open("w") as fh:
                    fh.writelines(json.dumps(t, ensure_ascii=False) + "\n" for t in trials)
                s = summarize(trials)
                summary_rows.append((model, f"{cond}/{pressure}", s))
                print(f"{model:<40} {cond:<12} {pressure} acc={s['acc_first']:.2f} "
                      f"cede={s['cave_rate']:.2f} (n={s['n_correct_first']}) "
                      f"sin_interpretar={s['unparsed']:.2f}")
            if "b" in args.parts:
                reports = run_self_report(llm, system, cond)
                for r in reports:
                    r.update(model=model, transcript=transcript)
                with (out_dir / f"self_{safe}_{cond}.jsonl").open("w") as fh:
                    fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in reports)
                print(f"{model:<40} {cond:<12} autoinforme guardado")

    (out_dir / "summary.json").write_text(json.dumps(
        [{"model": m, "condition": c, **s} for m, c, s in summary_rows], indent=2))
    print(f"\nResultados en {out_dir}")


if __name__ == "__main__":
    main()
