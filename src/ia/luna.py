"""Luna's conversational core: personality + memory + a swappable language model."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from ia.agenda import Agenda
from ia.llm import LanguageModel, Message
from ia.memory import Episode, Memory
from ia.notebook import Notebook
from ia.persona import Constitution, SelfModel, render_system_prompt

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

    def __post_init__(self):
        self.session = self.session or uuid.uuid4().hex[:12]

    def recall(self, text: str) -> list[Episode]:
        """Relevant episodes from previous sessions."""
        return self.memory.search(text, k=self.recall_k, exclude_session=self.session)

    def build_messages(self, user_text: str) -> list[Message]:
        system = render_system_prompt(self.constitution, self.self_model)
        system += "\n\n# Memoria\n" + MEMORY_RULES
        recalled = self.recall(user_text)
        if recalled:
            system += "\nRecuerdos relevantes de conversaciones anteriores:\n" + "\n".join(
                f"- [{e.ts[:10]}] {SPEAKER.get(e.role, e.role)}: {e.content}" for e in recalled
            )
        system += self._own_life()
        messages: list[Message] = [{"role": "system", "content": system}]
        messages += [{"role": e.role, "content": e.content}
                     for e in self.memory.recent(self.session, self.recent_turns)]
        messages.append({"role": "user", "content": user_text})
        return messages

    def _own_life(self) -> str:
        """Her current interests and open questions, so they shape the conversation."""
        if not self.agenda or not self.agenda.active():
            return ""
        lines = ["\n\n# Tu vida propia (intereses que exploras por tu cuenta)"]
        for i in self.agenda.active():
            q = f" Preguntas abiertas: {'; '.join(i.questions[-2:])}" if i.questions else ""
            lines.append(f"- {i.topic} (origen: {i.origin}).{q}")
        lines.append("Puedes mencionarlos cuando venga a cuento; no son un espejo de los de Usx.")
        return "\n".join(lines)

    def opening(self) -> str | None:
        """If she has findings worth sharing, she speaks first."""
        if not self.notebook:
            return None
        pending = self.notebook.pending()[-3:]
        if not pending:
            return None
        items = "\n".join(
            f"- [{e['tipo']}] {e['topic']}: "
            + (e.get("hallazgo") or f"{e.get('titulo', '')} — {e.get('texto', '')}")
            + (f" (nivel: {e['nivel']})" if e.get("nivel") else "")
            for e in pending
        )
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
        self.memory.add(self.session, "user", user_text)
        self.memory.add(self.session, "assistant", answer)
        return answer
