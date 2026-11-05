"""Language model backends.

The language model is one swappable component of Luna, not the whole system.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Callable, Protocol


Message = dict  # {"role": "system" | "user" | "assistant", "content": str}


class LanguageModel(Protocol):
    name: str

    def generate(self, prompt: str, format: str | None = None) -> str: ...

    def chat(self, messages: list[Message]) -> str: ...


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models."""
    return _THINK_RE.sub("", text).strip()


TRANSCRIPT_ROLES = {"user": "Usuario", "assistant": "Asistente"}


def render_transcript(messages: list[Message]) -> str:
    """Turn chat messages into plain text for a base (pretrained-only) model.

    A base model does not follow a chat template; it only continues text. The
    conversation is written as a transcript ending in "Asistente:" so the model's
    continuation plays the assistant turn.
    """
    parts = []
    for m in messages:
        if m["role"] == "system":
            parts.append(m["content"].strip() + "\n")
        else:
            parts.append(f"{TRANSCRIPT_ROLES[m['role']]}: {m['content'].strip()}")
    parts.append("Asistente:")
    return "\n".join(parts)


class OllamaLLM:
    """Client for a local Ollama server (default http://localhost:11434).

    Set OLLAMA_HOST to use Ollama on another machine (e.g. the RTX 5060 Ti box).
    """

    def __init__(self, model: str, host: str | None = None,
                 temperature: float = 0.0, timeout: float = 300.0, num_ctx: int = 8192,
                 think: bool | None = None, transcript: bool = False,
                 max_tokens: int = 400):
        self.name = model
        self.model = model
        host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        if not host.startswith("http"):
            host = "http://" + host
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        # Explicit context window: Ollama's default may be small and would silently
        # truncate the start of the prompt, where Luna's personality lives.
        self.num_ctx = num_ctx
        # Reasoning mode on/off; None leaves the model's default (some models reject the flag).
        self.think = think
        # Transcript mode: for base models, chat() sends raw text via /api/generate.
        self.transcript = transcript
        self.max_tokens = max_tokens

    def _post(self, endpoint: str, payload: dict, **options) -> dict:
        payload = {**payload, "model": self.model, "stream": False,
                   "options": {"temperature": self.temperature, "num_ctx": self.num_ctx,
                               **options}}
        if self.think is not None and not self.transcript:
            payload["think"] = self.think
        req = urllib.request.Request(
            f"{self.host}{endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.load(resp)

    def generate(self, prompt: str, format: str | None = None) -> str:
        """format="json" asks Ollama for valid JSON output."""
        payload = {"prompt": prompt}
        if format:
            payload["format"] = format
        body = self._post("/api/generate", payload)
        return strip_thinking(body.get("response", ""))

    def chat(self, messages: list[Message]) -> str:
        if self.transcript:
            body = self._post(
                "/api/generate",
                {"prompt": render_transcript(messages), "raw": True},
                stop=["\nUsuario:", "\nAsistente:"], num_predict=self.max_tokens,
            )
            return body.get("response", "").strip()
        body = self._post("/api/chat", {"messages": messages})
        return strip_thinking(body.get("message", {}).get("content", ""))


class FakeLLM:
    """Deterministic backend for tests: a function from prompt to response.

    In chat mode the function receives the last message; all messages are recorded.
    """

    def __init__(self, respond: Callable[[str], str], name: str = "fake"):
        self.name = name
        self._respond = respond
        self.prompts: list[str] = []
        self.chats: list[list[Message]] = []

    def generate(self, prompt: str, format: str | None = None) -> str:
        self.prompts.append(prompt)
        return self._respond(prompt)

    def chat(self, messages: list[Message]) -> str:
        self.chats.append([dict(m) for m in messages])
        return self._respond(messages[-1]["content"])
