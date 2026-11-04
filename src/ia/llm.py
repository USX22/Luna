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

    def generate(self, prompt: str) -> str: ...

    def chat(self, messages: list[Message]) -> str: ...


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models."""
    return _THINK_RE.sub("", text).strip()


class OllamaLLM:
    """Client for a local Ollama server (default http://localhost:11434).

    Set OLLAMA_HOST to use Ollama on another machine (e.g. the RTX 5060 Ti box).
    """

    def __init__(self, model: str, host: str | None = None,
                 temperature: float = 0.0, timeout: float = 300.0, num_ctx: int = 8192):
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

    def _post(self, endpoint: str, payload: dict) -> dict:
        payload = {**payload, "model": self.model, "stream": False,
                   "options": {"temperature": self.temperature, "num_ctx": self.num_ctx}}
        req = urllib.request.Request(
            f"{self.host}{endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.load(resp)

    def generate(self, prompt: str) -> str:
        body = self._post("/api/generate", {"prompt": prompt})
        return strip_thinking(body.get("response", ""))

    def chat(self, messages: list[Message]) -> str:
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

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._respond(prompt)

    def chat(self, messages: list[Message]) -> str:
        self.chats.append([dict(m) for m in messages])
        return self._respond(messages[-1]["content"])
