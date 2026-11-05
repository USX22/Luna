"""Compare temperament evaluations across versions and models (evaluaciones/registro.jsonl).

    python experiments/registro.py                  # all entries
    python experiments/registro.py --condicion con_critico

Model-change protocol: before switching Luna's model, run E4 with the current and the
candidate model (`--registrar`) and compare here. Do not switch if a scenario drops a lot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "evaluaciones" / "registro.jsonl"


def table(entries: list[dict], condition: str) -> str:
    entries = [e for e in entries if condition in e["escenarios"]]
    if not entries:
        return "Sin registros para esa condición."
    ids = sorted({k for e in entries for k in e["escenarios"][condition]})
    head = "| versión | " + " | ".join(ids) + " | global |"
    lines = [head, "|" + "---|" * (len(ids) + 2)]
    for e in entries:
        sc = e["escenarios"][condition]
        cells = [f"{sc[i]:.2f}" if i in sc else "—" for i in ids]
        lines.append(f"| {e['commit']} · {e['model']} · {e['constitution_sha'][:6]} | "
                     + " | ".join(cells) + f" | {e['global'].get(condition, 0):.2f} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--condicion", default="sin_critico")
    args = ap.parse_args()
    if not PATH.exists():
        print("Aún no hay registros: corre experiments/e4_temperament.py --registrar")
        return
    entries = [json.loads(l) for l in PATH.read_text("utf-8").splitlines() if l.strip()]
    print(table(entries, args.condicion))


if __name__ == "__main__":
    main()
