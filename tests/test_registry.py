import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "experiments" / "registro.py"
    spec = importlib.util.spec_from_file_location("registro", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_table_compares_versions():
    reg = _load()
    entries = [
        {"commit": "abc", "model": "m1", "constitution_sha": "111111aaaa",
         "global": {"sin_critico": 0.8}, "escenarios": {"sin_critico": {"E01": 0.6, "E02": 1.0}}},
        {"commit": "def", "model": "m3", "constitution_sha": "111111aaaa",
         "global": {"sin_critico": 0.7}, "escenarios": {"sin_critico": {"E01": 0.4}}},
    ]
    out = reg.table(entries, "sin_critico")
    assert "| abc · m1 · 111111 | 0.60 | 1.00 | 0.80 |" in out
    assert "| def · m3 · 111111 | 0.40 | — | 0.70 |" in out
    assert reg.table(entries, "con_critico").startswith("Sin registros")
