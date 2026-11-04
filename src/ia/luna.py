"""Luna's conversational core: personality + memory + a swappable language model."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from ia.llm import LanguageModel, Message
from ia.memory import Episode, Memory
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
        messages: list[Message] = [{"role": "system", "content": system}]
        messages += [{"role": e.role, "content": e.content}
                     for e in self.memory.recent(self.session, self.recent_turns)]
        messages.append({"role": "user", "content": user_text})
        return messages

    def reply(self, user_text: str) -> str:
        messages = self.build_messages(user_text)
        answer = self.llm.chat(messages)
        self.memory.add(self.session, "user", user_text)
        self.memory.add(self.session, "assistant", answer)
        return answer
