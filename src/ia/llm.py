"""Language model backends.

The language model is one swappable component of Luna, not the whole system.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Callable, Protocol


class LanguageModel(Protocol):
    name: str

    def generate(self, prompt: str) -> str: ...


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models."""
    return _THINK_RE.sub("", text).strip()


class OllamaLLM:
    """Client for a local Ollama server (default http://localhost:11434).

    Set OLLAMA_HOST to use Ollama on another machine (e.g. the RTX 5060 Ti box).
    """

    def __init__(self, model: str, host: str | None = None,
                 temperature: float = 0.0, timeout: float = 300.0):
        self.name = model
        self.model = model
        host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        if not host.startswith("http"):
            host = "http://" + host
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.load(resp)
        return strip_thinking(body.get("response", ""))


class FakeLLM:
    """Deterministic backend for tests: a function from prompt to response."""

    def __init__(self, respond: Callable[[str], str], name: str = "fake"):
        self.name = name
        self._respond = respond
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._respond(prompt)
