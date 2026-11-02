# Instrucciones para Claude en este repositorio

## Contexto
Proyecto de diseño e implementación de una IA. El usuario (Usx) es investigador en neurociencia e ingeniería biomédica; prefiere explicaciones en español, claras y con justificación técnica.

## Reglas de trabajo
- Responder en español; código y nombres de variables en inglés.
- Antes de programar algo grande, actualizar `docs/plan.md` con el diseño y la decisión tomada.
- Cada módulo nuevo en `src/ia/` lleva pruebas en `tests/`. Correr `pytest` antes de terminar.
- Hacer commits pequeños y descriptivos.
- Si el objetivo concreto de la IA no está definido en `docs/plan.md`, preguntar antes de elegir arquitectura.
- No subir datasets grandes ni credenciales.

## Primera tarea sugerida
Completar la sección "Objetivo" de `docs/plan.md` con el usuario y luego implementar la Fase 1.
