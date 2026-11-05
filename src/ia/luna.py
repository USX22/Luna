"""Luna's conversational core: personality + memory + a swappable language model."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ia.agenda import Agenda
from ia.beliefs import BeliefStore
from ia.llm import LanguageModel, Message
from ia.memory import Episode, Memory
from ia.notebook import Notebook
from ia.persona import Constitution, SelfModel, render_system_prompt
from ia.tools import Toolbox
from ia.workspace import Content, Workspace, make

if TYPE_CHECKING:
    from ia.critic import Critic

SPEAKER = {"user": "Usx", "assistant": "Luna"}

MEMORY_RULES = (
    "Solo puedes afirmar que recuerdas algo si aparece en tus recuerdos o en esta "
    "conversación. Si no está, di que no lo recuerdas; nunca inventes recuerdos."
)


@dataclass
class Luna:
    llm: LanguageModel
    constitution: Constitution
    self_model: SelfModel
    memory: Memory
    session: str = ""
    recent_turns: int = 12
    recall_k: int = 5
    agenda: Agenda | None = None
    notebook: Notebook | None = None
    toolbox: Toolbox | None = None
    beliefs: BeliefStore | None = None
    workspace: Workspace | None = None
    critic: "Critic | None" = None
    last_critique: list = None  # violations found in the last draft (for /critica)

    def __post_init__(self):
        self.session = self.session or uuid.uuid4().hex[:12]
        self.workspace = self.workspace or Workspace()

    def recall(self, text: str) -> list[Episode]:
        """Relevant episodes from previous sessions."""
        return self.memory.search(text, k=self.recall_k, exclude_session=self.session)

    def candidates(self, cue: str) -> list[Content]:
        """What each module proposes for the focus, given the current cue."""
        out: list[Content] = []
        for rank, e in enumerate(self.recall(cue)):
            module = "resumen" if e.role == "resumen" else "memoria"
            who = "" if module == "resumen" else f"{SPEAKER.get(e.role, e.role)}: "
            out.append(make(module, f"[{e.ts[:10]}] {who}{e.content}", cue, 0.1 / (rank + 1)))
        if self.beliefs:
            for b in self.beliefs.about(cue):
                who = "Usx cree" if b.holder == "usx" else "Tú crees"
                out.append(make("creencia", f"{who}: {b.describe()} ({b.level}, {b.ts[:10]})", cue))
            for old, new, ts in self.beliefs.changes("usx")[:3]:
                out.append(make("cambio", f"Usx antes creía «{old.describe()}» y desde {ts[:10]} "
                                          f"cree «{new.describe()}»", cue))
            for u, l in self.beliefs.disagreements()[:3]:
                out.append(make("desacuerdo", f"Usx: «{u.describe()}»; tú: «{l.describe()}»", cue))
        if self.agenda:
            for i in self.agenda.active():
                q = f" (pregunta abierta: {i.questions[-1]})" if i.questions else ""
                out.append(make("interes", f"{i.topic}, origen {i.origin}{q}", cue,
                                0.1 * i.learning_progress()))
        return out

    def build_messages(self, user_text: str) -> list[Message]:
        system = render_system_prompt(self.constitution, self.self_model)
        system += "\n\n# Memoria\n" + MEMORY_RULES
        focus = self.workspace.compete(self.candidates(user_text))
        if focus:
            system += ("\n\n# Tu foco ahora (lo que viene a tu mente; úsalo solo si es "
                       "pertinente)\n" + "\n".join(c.render() for c in focus))
            if any(c.module == "interes" for c in focus):
                system += ("\nTus intereses son tuyos, no un espejo de los de Usx; "
                           "menciónalos cuando venga a cuento.")
        messages: list[Message] = [{"role": "system", "content": system}]
        messages += [{"role": e.role, "content": e.content}
                     for e in self.memory.recent(self.session, self.recent_turns)
                     if e.role in ("user", "assistant")]
        messages.append({"role": "user", "content": user_text})
        return messages

    def opening(self) -> str | None:
        """If she has findings worth sharing, she speaks first."""
        if not self.notebook:
            return None
        pending = self.notebook.pending()[-3:]
        proposals = self.toolbox.proposals.pending() if self.toolbox else []
        if not pending and not proposals:
            return None
        items = "\n".join(
            f"- [{e['tipo']}] {e['topic']}: "
            + (e.get("hallazgo") or f"{e.get('titulo', '')} — {e.get('texto', '')}")
            + (f" (nivel: {e['nivel']})" if e.get("nivel") else "")
            + (f" [simulación: {e['interpretacion']}]" if e.get("interpretacion") else "")
            for e in pending
        )
        if proposals:
            items += "\nPropuestas que esperan su aprobación (dile el id y por qué):\n" + "\n".join(
                f"- #{p['id']} {p['tool']}: {p['reason']}" for p in proposals[-3:])
        messages = self.build_messages("")[:-1]
        messages.append({"role": "user", "content": (
            "[Nota interna, no es un mensaje de Usx: Usx acaba de abrir la conversación. "
            "Mientras no estaba, hiciste esto por tu cuenta:\n" + items + "\n"
            "Ábrele tú la conversación contándole lo que te parezca más interesante, a tu "
            "manera (humor mordaz y cariño antes del descubrimiento), con su nivel "
            "epistémico. Breve. No lo cuentes todo de golpe.]")})
        text = self.llm.chat(messages)
        self.memory.add(self.session, "assistant", text)
        self.notebook.mark_shared({e["id"] for e in pending})
        return text

    def reply(self, user_text: str) -> str:
        messages = self.build_messages(user_text)
        answer = self.llm.chat(messages)
        self.last_critique = []
        if self.critic is not None:
            context = "\n".join(f"{m['role']}: {m['content']}" for m in messages[1:])
            critique = self.critic.check(answer, context)
            if not critique.ok:
                self.last_critique = critique.violations
                messages.append({"role": "assistant", "content": answer})
                messages.append({"role": "user", "content": (
                    "[Nota interna de tu crítico, no es Usx: tu respuesta viola tu "
                    f"constitución: {critique.feedback(self.critic.rules)}. Reescríbela "
                    "respetando tus principios. Responde solo con la nueva versión.]")})
                answer = self.llm.chat(messages)
        self.memory.add(self.session, "user", user_text)
        self.memory.add(self.session, "assistant", answer)
        return answer
