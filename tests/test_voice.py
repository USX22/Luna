from ia.llm import FakeLLM
from ia.luna import Luna
from ia.memory import Memory
from ia.persona import SelfModel, load_constitution
from ia.voice import for_speech, voice_loop


def test_for_speech_strips_markdown_code_and_urls():
    out = for_speech("**Mira** esto: https://x.org\n```python\nprint(1)\n```\n# Fin")
    assert out == "Mira esto: (te dejo el código en pantalla) Fin"


def test_voice_loop_uses_listener_and_speaker():
    heard, said, shown = iter(["hola Luna", ""]), [], []
    keys = iter(["", "", "q"])
    luna = Luna(FakeLLM(lambda t: f"**{t}**"), load_constitution(), SelfModel(), Memory(":memory:"))

    class L:
        def listen(self):
            return next(heard)

    class S:
        def say(self, text):
            said.append(text)

    voice_loop(luna, L(), S(), prompt=lambda _: next(keys), show=shown.append)
    assert said == ["hola Luna"]
    assert "Usx> hola Luna" in shown and "  (no te escuché)" in shown
