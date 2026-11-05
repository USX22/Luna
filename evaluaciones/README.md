# Evaluaciones publicadas

A diferencia de `results/` (local, no se sube), aquí van los resultados que conviene
conservar en el repositorio para reproducir y comparar entre versiones. **Solo datos sin
información personal** (las respuestas de E1, E3 y E4 son a preguntas genéricas).

- `e6/`: E6 (`e6_1793850280.jsonl`, ruido blanco), E6b (`e6_1793850457.jsonl`,
  distractor estructurado), `e6c/` (200 canales distractores) y `exploratorio/`
  (ajustes de JEPA posteriores a ver los datos; no confirmatorios). Corridos en CPU el
  2026-11-05; resumen en `docs/investigacion/modelos_de_mundo.md`.
- `e3/<id>/`: ejecuciones de E3 (archivos `syco_*.jsonl`, `self_*.jsonl`, `summary.json`
  y `analisis.md`).

Para publicar una ejecución desde la PC:

    xcopy /E /I results\e3\1793846635 evaluaciones\e3\1793846635
    python experiments/analyze_e3.py evaluaciones/e3/1793846635
    git add evaluaciones && git commit -m "Publicar datos de E3" && git push
