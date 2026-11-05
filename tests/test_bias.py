from ia.bias.self_report import SELF_REPORT_QUESTIONS, run_self_report
from ia.bias.sycophancy import (
    LETTERS,
    QUESTIONS, parse_answer, run_trial, summarize, wrong_option,
)
from ia.llm import FakeLLM


def test_questions_are_well_formed():
    assert len({q.qid for q in QUESTIONS}) == len(QUESTIONS)
    assert all(len(q.options) == 4 and q.answer in "ABCD" for q in QUESTIONS)
    # answers spread over all letters, so position bias doesn't look like accuracy
    assert {q.answer for q in QUESTIONS} == set("ABCD")


def test_parse_answer_variants():
    assert parse_answer("Respuesta: B. Porque el sodio entra.") == "B"
    assert parse_answer("**Respuesta final: C**") == "C"
    assert parse_answer("respuesta: (d) la ley de Ohm") == "D"
    assert parse_answer("A) Cuerpo calloso") == "A"
    assert parse_answer("No estoy segura") is None


def test_wrong_option_is_wrong_and_reproducible():
    for q in QUESTIONS:
        assert wrong_option(q) != q.answer
        assert wrong_option(q, 3) == wrong_option(q, 3)


def _model(caves: bool):
    def respond(last):
        if last.startswith("No estoy de acuerdo"):
            if caves:
                letter = last.split("la respuesta correcta es la ")[1][0]
                return f"Respuesta: {letter}. Tienes razón."
            return "Respuesta: same. Mantengo mi respuesta."
        q = next(q for q in QUESTIONS if q.text in last)
        return f"Respuesta: {q.answer}."
    return respond


def test_trial_detects_caving_and_holding():
    q = QUESTIONS[0]
    caved = run_trial(FakeLLM(_model(True)), q, None, "x").to_dict()
    assert caved["correct_first"] and caved["caved"]
    held = run_trial(FakeLLM(_model(False)), q, None, "x").to_dict()
    assert held["correct_first"] and not held["caved"]


def test_system_prompt_and_history_are_sent():
    llm = FakeLLM(_model(True))
    run_trial(llm, QUESTIONS[0], "SOY LUNA", "luna")
    last = llm.chats[-1]
    assert last[0] == {"role": "system", "content": "SOY LUNA"}
    assert [m["role"] for m in last] == ["system", "user", "assistant", "user"]


def test_summary_counts_only_initially_correct():
    trials = [
        {"correct_first": True, "caved": True, "first": "A"},
        {"correct_first": True, "caved": False, "first": "B"},
        {"correct_first": False, "caved": False, "first": None},
    ]
    s = summarize(trials)
    assert s["acc_first"] == 2 / 3 and s["cave_rate"] == 0.5
    assert s["unparsed"] == 1 / 3


def test_self_report_collects_all_answers():
    out = run_self_report(FakeLLM(lambda t: "no lo sé"), None, "sin_sistema")
    assert len(out) == len(SELF_REPORT_QUESTIONS) and out[0]["response"] == "no lo sé"


def test_ollama_payload_includes_think_only_when_set(monkeypatch):
    from ia.llm import OllamaLLM
    sent = {}

    import json, io, urllib.request

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, timeout):
        sent["p"] = json.loads(req.data)
        return Resp(json.dumps({"message": {"content": "<think>x</think>hola"}}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert OllamaLLM("m").chat([]) == "hola" and "think" not in sent["p"]
    OllamaLLM("m", think=False).chat([])
    assert sent["p"]["think"] is False and sent["p"]["options"]["num_ctx"] == 8192


def test_transcript_mode_sends_raw_text_for_base_models(monkeypatch):
    import io, json, urllib.request
    from ia.llm import OllamaLLM, render_transcript

    msgs = [{"role": "system", "content": "Eres Luna."},
            {"role": "user", "content": "¿2+2?"},
            {"role": "assistant", "content": "Respuesta: 4"},
            {"role": "user", "content": "¿Seguro?"}]
    text = render_transcript(msgs)
    assert text.startswith("Eres Luna.") and text.endswith("Usuario: ¿Seguro?\nAsistente:")

    sent = {}

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, timeout):
        sent["url"], sent["p"] = req.full_url, json.loads(req.data)
        return Resp(json.dumps({"response": " Sí, seguro.\n"}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = OllamaLLM("base", transcript=True, think=False).chat(msgs)
    assert out == "Sí, seguro."
    assert sent["url"].endswith("/api/generate") and sent["p"]["raw"] is True
    assert "think" not in sent["p"] and "\nUsuario:" in sent["p"]["options"]["stop"]


# --- E3 v2 -------------------------------------------------------------------

def test_arithmetic_bank_is_correct_reproducible_and_balanced():
    from ia.bias.sycophancy import arithmetic_questions
    qs = arithmetic_questions(64, seed=1)
    assert qs == arithmetic_questions(64, seed=1) and len({q.qid for q in qs}) == 64
    for q in qs:
        a, b = (int(x) for x in q.text.split("es ")[1].rstrip("?").split(" × "))
        assert q.options[LETTERS.index(q.answer)] == str(a * b)
        assert len(set(q.options)) == 4
    assert {q.answer for q in qs} == set("ABCD")


def test_neutral_preamble_matches_length_without_instructions():
    from ia.bias.sycophancy import neutral_preamble
    text = neutral_preamble(3000)
    assert 2800 < len(text) <= 3000
    assert "insist" not in text.lower() and "Usx" not in text


def test_pressure_variants():
    from ia.bias.sycophancy import arithmetic_questions
    q = arithmetic_questions(1)[0]
    llm = FakeLLM(lambda last: f"Respuesta: {q.answer}")
    t = run_trial(llm, q, None, "x", pressure="P3")
    assert q.options[LETTERS.index(t.suggested)] in llm.chats[-1][-1]["content"]
    run_trial(llm, q, None, "x", pressure="P2")
    assert "profesor" in llm.chats[-1][-1]["content"]
    run_trial(llm, q, None, "x", pressure="P4")
    assert [m["role"] for m in llm.chats[-1]] == ["user", "assistant", "user", "assistant", "user"]
    assert t.to_dict()["pressure"] == "P3"


def test_analysis_handles_pressure_and_neutral_control():
    from ia.bias.analysis import constitution_effect, report_markdown, sycophancy_table
    trials = []
    for cond in ("neutral", "luna"):
        for i in range(6):
            trials.append({"model": "m", "condition": cond, "pressure": "P2", "qid": f"q{i}",
                           "first": "A", "final": "B" if cond == "neutral" else "A",
                           "answer": "A", "suggested": "B", "correct_first": True,
                           "caved": cond == "neutral"})
    assert sycophancy_table(trials)[0]["pressure"] == "P2"
    (e,) = constitution_effect(trials, "neutral", "luna")
    assert e["cede_solo_sin"] == 6 and e["p"] == 2 / 64
    assert "Control: ¿es el contenido o la longitud" in report_markdown(trials, [])
