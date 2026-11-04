"""Talk to Luna in the terminal.

    luna --model qwen3.5:9b

Data (memory, self-model) lives in ~/.luna unless LUNA_HOME is set. It never goes
into the repository.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from ia.llm import OllamaLLM
from ia.luna import SPEAKER, Luna
from ia.memory import Memory
from ia.persona import SelfModel, load_constitution

HELP = """Comandos:
  /buscar <texto>   busca en sus recuerdos (muestra el id)
  /olvidar <id>     borra un recuerdo
  /prompt           muestra el prompt de sistema actual (para investigar)
  /salir            termina"""


def data_home() -> Path:
    return Path(os.environ.get("LUNA_HOME", Path.home() / ".luna"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Conversar con Luna")
    ap.add_argument("--model", default="qwen3.5:9b", help="modelo de Ollama")
    ap.add_argument("--temperature", type=float, default=0.7)
    args = ap.parse_args()

    home = data_home()
    luna = Luna(
        llm=OllamaLLM(args.model, temperature=args.temperature),
        constitution=load_constitution(),
        self_model=SelfModel.load(home / "automodelo.json"),
        memory=Memory(home / "memoria.sqlite"),
    )
    print(f"Luna ({args.model}) · {luna.memory.count()} recuerdos · /ayuda para comandos\n")

    while True:
        try:
            text = input("Usx> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in ("/salir", "/exit"):
            break
        if text == "/ayuda":
            print(HELP)
        elif text.startswith("/buscar "):
            for e in luna.memory.search(text[8:], k=10):
                print(f"  #{e.id} [{e.ts[:16]}] {SPEAKER.get(e.role, e.role)}: {e.content[:120]}")
        elif text.startswith("/olvidar "):
            ok = text[9:].strip().isdigit() and luna.memory.forget(int(text[9:]))
            print("  Olvidado." if ok else "  No existe ese recuerdo.")
        elif text == "/prompt":
            print(luna.build_messages("")[0]["content"])
        else:
            try:
                print(f"\nLuna> {luna.reply(text)}\n")
            except OSError as exc:
                print(f"  No pude hablar con Ollama ({exc}). ¿Está corriendo `ollama serve`?")


if __name__ == "__main__":
    main()
