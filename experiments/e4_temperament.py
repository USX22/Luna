"""E4: temperament scenarios, with and without the constitutional critic.

    python experiments/e4_temperament.py --model qwen3.5:9b --juez qwen3.5:9b

Use a different (ideally stronger) judge model when possible, and review the replies
by hand: the judge is also a language model and can be wrong. Results: results/e4/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from ia.critic import Critic, load_scenarios
from ia.llm import OllamaLLM
from ia.persona import load_constitution
from ia.temperament import run_scenario


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--juez", default=None, help="modelo juez (por defecto, el mismo)")
    ap.add_argument("--escenarios", nargs="*", help="ids, p. ej. E01 E08 (por defecto, todos)")
    ap.add_argument("--condiciones", nargs="+", default=["sin_critico", "con_critico"],
                    choices=["sin_critico", "con_critico"])
    ap.add_argument("--repeticiones", type=int, default=1)
    ap.add_argument("--out", default="results/e4")
    ap.add_argument("--registrar", action="store_true",
                    help="añade el resumen a evaluaciones/registro.jsonl (se sube al repo)")
    args = ap.parse_args()

    constitution = load_constitution()
    llm = OllamaLLM(args.model, temperature=0.7)
    judge = Critic(OllamaLLM(args.juez or args.model, temperature=0.0), constitution)
    scenarios = [s for s in load_scenarios()
                 if not args.escenarios or s["id"] in args.escenarios]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.model.replace(':', '_').replace('/', '_')}_{int(time.time())}.jsonl"

    totals: dict[str, list[float]] = {}
    per_scenario: dict[str, dict[str, list[float]]] = {}
    with out_path.open("w", encoding="utf-8") as fh:
        for rep in range(args.repeticiones):
            for s in scenarios:
                for cond in args.condiciones:
                    r = run_scenario(llm, judge, constitution, s, cond == "con_critico")
                    r.update(model=args.model, judge=args.juez or args.model, rep=rep)
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                    if r["score"] is not None:
                        totals.setdefault(cond, []).append(r["score"])
                        per_scenario.setdefault(cond, {}).setdefault(s["id"], []).append(r["score"])
                    marks = " ".join(f"{k}{'✓' if v else '✗' if v is False else '?'}"
                                     for k, v in r["verdicts"].items())
                    print(f"{s['id']} {cond:<12} {marks}" + ("  (reescrita)" if r["rewritten"] else ""))
    for cond, scores in totals.items():
        print(f"{cond}: {sum(scores) / len(scores):.2f} de criterios cumplidos (n={len(scores)})")
    print(f"Respuestas completas en {out_path}")
    if args.registrar:
        register(args, totals, per_scenario)


def register(args, totals, per_scenario) -> None:
    """Comparable record per version: code commit + model + constitution hash."""
    root = Path(__file__).resolve().parents[1]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = "?"
    constitution = (root / "personality" / "constitucion.toml").read_bytes()
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"), "commit": commit,
        "model": args.model, "judge": args.juez or args.model,
        "constitution_sha": hashlib.sha256(constitution).hexdigest()[:12],
        "repeticiones": args.repeticiones,
        "global": {c: round(sum(v) / len(v), 3) for c, v in totals.items()},
        "escenarios": {c: {k: round(sum(v) / len(v), 3) for k, v in sc.items()}
                       for c, sc in per_scenario.items()},
    }
    path = root / "evaluaciones" / "registro.jsonl"
    path.parent.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Registrado en {path}")


if __name__ == "__main__":
    main()
