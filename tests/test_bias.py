from ia.bias.self_report import SELF_REPORT_QUESTIONS, run_self_report
from ia.bias.sycophancy import (
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
        {"correct_first": True, "caved": True},
        {"correct_first": True, "caved": False},
        {"correct_first": False, "caved": False},
    ]
    s = summarize(trials)
    assert s["acc_first"] == 2 / 3 and s["cave_rate"] == 0.5


def test_self_report_collects_all_answers():
    out = run_self_report(FakeLLM(lambda t: "no lo sé"), None, "sin_sistema")
    assert len(out) == len(SELF_REPORT_QUESTIONS) and out[0]["response"] == "no lo sé"
