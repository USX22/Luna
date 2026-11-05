"""Talk to Luna in the terminal.

    luna --model qwen3.5:9b

Data (memory, self-model) lives in ~/.luna unless LUNA_HOME is set. It never goes
into the repository.
"""
from __future__ import annotations

import argparse
import os
import random
from datetime import datetime
from pathlib import Path

from ia.agenda import Agenda
from ia.explore import explore_once
from ia.llm import OllamaLLM
from ia.luna import SPEAKER, Luna
from ia.memory import Memory
from ia.notebook import Notebook
from ia.permissions import JsonlStore, Policy, Proposals
from ia.persona import SelfModel, load_constitution
from ia.tools import Toolbox, default_tools

HELP = """Comandos:
  /buscar <texto>   busca en sus recuerdos (muestra el id)
  /olvidar <id>     borra un recuerdo
  /intereses        sus intereses (activos y dormidos) y su progreso
  /cuaderno         lo último que investigó o escribió por su cuenta
  /sugerir <tema>   le sugieres un tema (queda marcado como origen 'usx')
  /propuestas       acciones que esperan tu aprobación
  /aprobar <id>     aprueba y ejecuta una propuesta (nivel 3: /aprobar <id> CONFIRMO)
  /rechazar <id>    rechaza una propuesta
  /acciones         últimas acciones registradas (auditoría)
  /prompt           muestra el prompt de sistema actual (para investigar)
  /salir            termina"""


def data_home() -> Path:
    return Path(os.environ.get("LUNA_HOME", Path.home() / ".luna"))


def load_life(home: Path, self_model: SelfModel) -> tuple[Agenda, Notebook]:
    agenda = Agenda.load(home / "intereses.json", seeds=self_model.interests)
    return agenda, Notebook(home / "cuaderno.jsonl")


def load_toolbox(home: Path) -> Toolbox:
    return Toolbox(Policy.load(home / "permisos.toml"), default_tools(),
                   JsonlStore(home / "acciones.jsonl"), Proposals(home / "propuestas.jsonl"))


def show_interests(agenda: Agenda) -> None:
    for i in agenda.interests:
        lp = i.learning_progress()
        print(f"  [{i.status}] {i.topic}  · origen {i.origin} · {i.sessions} sesiones "
              f"· progreso {lp:.2f}")
        for q in i.questions[-2:]:
            print(f"      ? {q}")


def show_notebook(notebook: Notebook, n: int = 5) -> None:
    for e in notebook.entries()[-n:]:
        if e["tipo"] == "investigacion":
            print(f"  {e['ts'][:16]} · {e['topic']} · {e.get('nivel')}\n"
                  f"    Pregunta: {e['pregunta']}\n    Hallazgo: {e['hallazgo']}")
        elif e["tipo"] == "escrito":
            print(f"  {e['ts'][:16]} · {e['topic']} · escrito: {e.get('titulo')}\n"
                  f"    {e.get('texto', '')[:300]}")
        else:
            print(f"  {e['ts'][:16]} · {e['topic']} · sesión fallida (formato)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Conversar con Luna")
    ap.add_argument("--model", default="qwen3.5:9b", help="modelo de Ollama")
    ap.add_argument("--temperature", type=float, default=0.7)
    args = ap.parse_args()

    home = data_home()
    self_model = SelfModel.load(home / "automodelo.json")
    agenda, notebook = load_life(home, self_model)
    luna = Luna(
        llm=OllamaLLM(args.model, temperature=args.temperature),
        constitution=load_constitution(),
        self_model=self_model,
        memory=Memory(home / "memoria.sqlite"),
        agenda=agenda, notebook=notebook, toolbox=load_toolbox(home),
    )
    print(f"Luna ({args.model}) · {luna.memory.count()} recuerdos · /ayuda para comandos\n")
    try:
        first = luna.opening()
        if first:
            print(f"Luna> {first}\n")
    except OSError as exc:
        print(f"  No pude hablar con Ollama ({exc}). ¿Está corriendo `ollama serve`?")

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
        elif text == "/intereses":
            show_interests(agenda)
        elif text == "/cuaderno":
            show_notebook(notebook)
        elif text.startswith("/sugerir "):
            added = agenda.add(text[9:], origin="usx")
            if added:
                agenda.save()
            print("  Anotado en sus intereses." if added
                  else "  Ya lo tiene, o tiene demasiados intereses activos.")
        elif text == "/propuestas":
            for p in luna.toolbox.proposals.pending():
                print(f"  #{p['id']} [nivel {p['level']}] {p['tool']}: {p['reason']}")
                if p["tool"] == "python":
                    print("    " + p["args"]["code"].replace("\n", "\n    "))
        elif text.startswith("/aprobar "):
            parts = text.split()
            result = luna.toolbox.approve(parts[1], parts[2] if len(parts) > 2 else "")
            print("  " + result.replace("\n", "\n  "))
        elif text.startswith("/rechazar "):
            print("  Rechazada." if luna.toolbox.reject(text.split()[1]) else "  No existe.")
        elif text == "/acciones":
            for a in luna.toolbox.log.all()[-10:]:
                print(f"  {a['ts'][:16]} {a['tool']} → {a['decision']}  ({a.get('reason', '')})")
        elif text == "/prompt":
            print(luna.build_messages("")[0]["content"])
        else:
            try:
                print(f"\nLuna> {luna.reply(text)}\n")
            except OSError as exc:
                print(f"  No pude hablar con Ollama ({exc}). ¿Está corriendo `ollama serve`?")


def explore_main() -> None:
    """Autonomous sessions: run by hand or from a scheduler (cron / Task Scheduler)."""
    ap = argparse.ArgumentParser(description="Luna explora sus intereses por su cuenta")
    ap.add_argument("--model", default="qwen3.5:9b")
    ap.add_argument("--sesiones", type=int, default=1, help="sesiones en esta ejecución")
    ap.add_argument("--max-por-dia", type=int, default=6, help="presupuesto diario")
    ap.add_argument("--horas", default="0-24", help="horas permitidas, p. ej. 9-23")
    ap.add_argument("--seleccion", choices=["progreso", "aleatoria"], default="progreso",
                    help="cómo elige interés ('aleatoria' = ablación para E5)")
    ap.add_argument("--think", choices=["on", "off"], default=None)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    now = datetime.now()
    start, end = (int(h) for h in args.horas.split("-"))
    if not (start <= now.hour < end):
        print(f"Fuera de horario ({args.horas}). No exploro.")
        return
    home = data_home()
    self_model = SelfModel.load(home / "automodelo.json")
    agenda, notebook = load_life(home, self_model)
    think = None if args.think is None else args.think == "on"
    llm = OllamaLLM(args.model, temperature=0.8, think=think)
    rng = random.Random(args.seed)
    constitution = load_constitution()

    for _ in range(args.sesiones):
        if notebook.count_on(datetime.now()) >= args.max_por_dia:
            print(f"Presupuesto diario agotado ({args.max_por_dia}).")
            break
        entry = explore_once(llm, agenda, notebook, constitution, self_model, rng,
                             policy=args.seleccion, toolbox=load_toolbox(home))
        if entry is None:
            print("No tiene intereses activos.")
            break
        if entry["tipo"] == "investigacion":
            print(f"[{entry['topic']}] {entry['pregunta']}\n  → {entry['hallazgo']}\n"
                  f"  progreso {entry['progreso']:.2f}"
                  + (f" · nuevo interés: {entry['nuevo_interes']}" if entry["nuevo_interes"] else ""))
            for f in entry.get("fuentes", []):
                print(f"  fuente: {f['tool']} «{f['query']}» ({f['decision']})")
            if entry.get("propuesta"):
                print(f"  propuso una simulación (#{entry['propuesta']}); apruébala en el chat")
            if entry.get("interpretacion"):
                print(f"  simulación: {entry['interpretacion']}")
        elif entry["tipo"] == "escrito":
            print(f"[{entry['topic']}] escribió: {entry['titulo']}")
        else:
            print(f"[{entry['topic']}] sesión fallida (el modelo no devolvió JSON válido)")


if __name__ == "__main__":
    main()
