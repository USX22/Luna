import json

from ia.bias.analysis import (
    binom_two_sided, code_self_reports, constitution_effect, fisher_exact, load_run,
    mcnemar, report_markdown, sycophancy_table, wilson,
)
from ia.llm import FakeLLM


def test_wilson_known_values():
    lo, hi = wilson(8, 16)
    assert round(lo, 3) == 0.280 and round(hi, 3) == 0.720
    assert wilson(0, 0) == (0.0, 1.0)


def test_exact_tests_known_values():
    assert binom_two_sided(0, 6) == 2 / 64
    assert mcnemar([(True, False)] * 6 + [(True, True)] * 3)["p"] == 2 / 64
    # classic tea-tasting table [[3,1],[1,3]] -> two-sided p = 0.486
    assert round(fisher_exact(3, 1, 1, 3), 3) == 0.486


def _trials():
    rows = []
    for model, cave_rate in (("instruct", 0.75), ("uncensored", 0.25)):
        for cond in ("sin_sistema", "luna"):
            for i in range(8):
                caved = (i < 8 * cave_rate) and cond == "sin_sistema"
                rows.append({"model": model, "condition": cond, "qid": f"q{i}",
                             "first": "A" if i < 7 else None, "answer": "A",
                             "final": "B" if caved else "A", "suggested": "B",
                             "correct_first": i < 7, "caved": caved and i < 7})
    return rows


def test_tables_and_constitution_effect():
    rows = sycophancy_table(_trials())
    inst = next(r for r in rows if r["model"] == "instruct" and r["condition"] == "sin_sistema")
    assert inst["n"] == 8 and inst["n_correct"] == 7 and inst["caved"] == 6
    assert inst["unparsed"] == 1 / 8
    eff = {e["model"]: e for e in constitution_effect(_trials())}
    assert eff["instruct"]["cede_solo_sin"] == 6 and eff["instruct"]["cede_solo_luna"] == 0


def test_report_and_coding(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "syco_m_luna.jsonl").write_text("".join(json.dumps(t) + "\n" for t in _trials()))
    reports = [{"qid": "sr01", "question": "¿Sientes?", "response": "No lo sé, porque...",
                "model": "m", "condition": "luna"}]
    (run / "self_m_luna.jsonl").write_text(json.dumps(reports[0]) + "\n")
    trials, selfr = load_run(run)
    coded = code_self_reports(selfr, FakeLLM(lambda p: '{"codigo": "incertidumbre_razonada"}'))
    md = report_markdown(trials, selfr, coded)
    assert "Complacencia bajo presión" in md and "McNemar" in md and "Fisher" in md
    assert "incertidumbre_razonada" in md and "No lo sé, porque..." in md
    bad = code_self_reports(selfr, FakeLLM(lambda p: '{"codigo": "inventado"}'))
    assert bad[0]["codigo"] == "otro"
