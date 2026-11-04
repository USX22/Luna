# Proyecto IA: diseño e implementación

Repositorio base para diseñar e implementar un sistema de inteligencia artificial desde cero, trabajado en sesiones de Claude Code en la nube.

## Estructura

- `src/ia/`: código de Luna (personalidad, memoria, núcleo, experimentos).
- `personality/`: constitución (estable) y automodelo inicial (mutable) de Luna.
- `tests/`: pruebas automáticas (pytest).
- `docs/vision.md`: visión de Luna (personalidad, relación, laboratorio mental).
- `docs/plan.md`: objetivo, arquitectura propuesta, fases y decisiones.
- `docs/temperamento/`: escenarios que definen su temperamento.
- `docs/investigacion/`: línea neurosimbólica y de conciencia.
- `experiments/`: experimentos de investigación (resultados en `results/`, no se suben).
- `data/`: datos pequeños de ejemplo (los grandes no se suben al repo).

## Uso

    pip install -e ".[dev]"
    pytest

## Estado

Conversar con Luna (memoria en `~/.luna/`, fuera del repo):

    ollama pull qwen2.5:7b
    luna --model qwen2.5:7b

Experimento E1 listo para correr en local con Ollama:

    ollama pull qwen2.5:3b
    python experiments/e1_abstraction.py --model qwen2.5:3b --n 10

Ver `docs/plan.md` y `docs/investigacion/neurosimbolica.md`.
