"""Analyse an E3 run and write analisis.md next to the results.

    python experiments/analyze_e3.py                       # latest run in results/e3
    python experiments/analyze_e3.py results/e3/1762300000 --codificar --juez qwen3.5:9b
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ia.bias.analysis import code_self_reports, load_run, report_markdown
from ia.llm import OllamaLLM


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", nargs="?", help="carpeta de la ejecución (por defecto, la última)")
    ap.add_argument("--codificar", action="store_true",
                    help="clasifica los autoinformes con un modelo juez")
    ap.add_argument("--juez", default="qwen3.5:9b")
    args = ap.parse_args()

    run = Path(args.run) if args.run else max(Path("results/e3").iterdir(), key=lambda p: p.name)
    trials, reports = load_run(run)
    coded = None
    if args.codificar and reports:
        coded = code_self_reports(reports, OllamaLLM(args.juez, temperature=0.0))
        (run / "autoinformes_codificados.jsonl").write_text(
            "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in coded), "utf-8")
    md = report_markdown(trials, reports, coded)
    (run / "analisis.md").write_text(md, "utf-8")
    print(md.split("## E3b. Respuestas completas")[0])
    print(f"Informe completo: {run / 'analisis.md'}")


if __name__ == "__main__":
    main()
