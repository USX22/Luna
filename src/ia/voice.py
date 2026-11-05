"""Voice for Luna (phase 8, v0): local speech-to-text and text-to-speech.

Backends are swappable; heavy dependencies are imported lazily (extra "voz"):
  - WhisperListener: faster-whisper on the GPU, push-to-talk with Enter.
  - SystemSpeaker: pyttsx3 with an installed Spanish system voice (works offline;
    quality depends on the OS voices). A better neural voice (e.g. Piper) can replace
    it later without touching the loop.
Not tested on real audio hardware yet.
"""
from __future__ import annotations

import re
from typing import Callable, Protocol

SAMPLE_RATE = 16_000


class Listener(Protocol):
    def listen(self) -> str: ...


class Speaker(Protocol):
    def say(self, text: str) -> None: ...


def for_speech(text: str) -> str:
    """Remove markdown and URLs so the voice doesn't read symbols aloud."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"```.*?```", " (te dejo el código en pantalla) ", text, flags=re.DOTALL)
    text = re.sub(r"[*_#`>|]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


class WhisperListener:
    def __init__(self, model_size: str = "small", language: str = "es",
                 wait: Callable[[str], str] = input):
        import numpy as np  # noqa: F401  (fail early if extras are missing)
        import sounddevice  # noqa: F401
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_size, device="auto", compute_type="auto")
        self.language = language
        self.wait = wait

    def listen(self) -> str:
        import numpy as np
        import sounddevice as sd
        frames: list = []
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            callback=lambda data, *_: frames.append(data.copy())):
            self.wait("  🎙  grabando… (Enter para terminar)")
        if not frames:
            return ""
        audio = np.concatenate(frames)[:, 0]
        segments, _ = self.model.transcribe(audio, language=self.language, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()


class SystemSpeaker:
    def __init__(self, language_hint: str = "es"):
        import pyttsx3
        self.engine = pyttsx3.init()
        for voice in self.engine.getProperty("voices"):
            ident = f"{voice.id} {voice.name} {getattr(voice, 'languages', '')}".lower()
            if language_hint in ident or "spanish" in ident or "español" in ident:
                self.engine.setProperty("voice", voice.id)
                break

    def say(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()


def voice_loop(luna, listener: Listener, speaker: Speaker,
               prompt: Callable[[str], str] = input, show: Callable[[str], None] = print,
               max_turns: int | None = None) -> None:
    first = luna.opening()
    if first:
        show(f"Luna> {first}")
        speaker.say(for_speech(first))
    turns = 0
    while max_turns is None or turns < max_turns:
        if prompt("[Enter para hablar · q para salir] ").strip().lower() == "q":
            break
        text = listener.listen()
        if not text:
            show("  (no te escuché)")
            continue
        show(f"Usx> {text}")
        answer = luna.reply(text)
        show(f"Luna> {answer}")
        speaker.say(for_speech(answer))
        turns += 1
