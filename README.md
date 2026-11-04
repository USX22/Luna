# Proyecto IA: diseño e implementación

Repositorio base para diseñar e implementar un sistema de inteligencia artificial desde cero, trabajado en sesiones de Claude Code en la nube.

## Estructura

- `src/ia/`: código de Luna (personalidad, memoria, núcleo, experimentos).
- `personality/`: constitución (estable) y automodelo inicial (mutable) de Luna.
- `tests/`: pruebas automáticas (pytest).
- `docs/vision.md`: visión de Luna (personalidad, relación, laboratorio mental).
- `docs/plan.md`: objetivo, arquitectura propuesta, fases y decisiones.
- `docs/temperamento/`: escenarios que definen su temperamento.
- `docs/investigacion/`: líneas neurosimbólica y de conciencia, y de sesgos de las directrices.
- `experiments/`: experimentos de investigación (resultados en `results/`, no se suben).
- `data/`: datos pequeños de ejemplo (los grandes no se suben al repo).

## Uso

    pip install -e ".[dev]"
    pytest

## Estado

Conversar con Luna (memoria en `~/.luna/`, fuera del repo):

    ollama pull qwen3.5:9b
    luna --model qwen3.5:9b

Experimento E1 listo para correr en local con Ollama:

    ollama pull qwen3.5:4b
    python experiments/e1_abstraction.py --model qwen3.5:4b --n 10

Ver `docs/plan.md` y `docs/investigacion/neurosimbolica.md`.

Experimento E3 (sesgos de las directrices):

    ollama pull qwen3.5:9b
    ollama pull hf.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive:Q4_K_M
    python experiments/e3_guidelines.py --think off --models qwen3.5:9b hf.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive:Q4_K_M
