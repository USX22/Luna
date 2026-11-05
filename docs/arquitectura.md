# Arquitectura de Luna (v1, 2026-11-05)

Idea central: **la identidad de Luna vive en su estado persistente**, no en el modelo
de lenguaje. El modelo es un sustrato intercambiable que genera texto; todo lo demás
(quién es, qué recuerda, qué cree, qué le interesa, qué puede hacer) son estructuras
explícitas que construimos nosotros.

```
                 Usx (texto: luna · voz: luna-voz)
                                │
              ┌─────────────────▼──────────────────┐
              │ Núcleo (src/ia/luna.py)            │
              │  constitución + automodelo          │
              │  + FOCO (espacio de trabajo global) │──► modelo local (Ollama)
              │  + crítico constitucional (opc.)    │◄── borrador → revisión
              └──▲───────▲────────▲────────▲───────┘
   candidatos al foco: │        │        │
   ┌────────────┐ ┌────┴─────┐ ┌┴───────┐ ┌┴──────────┐
   │ Memoria    │ │Creencias │ │Intereses│ │Propuestas │
   │ episódica  │ │simbólicas│ │(agenda) │ │y permisos │
   │ + resúmenes│ │tripletas │ │cuaderno │ │auditoría  │
   └─────▲──────┘ └────▲─────┘ └───▲─────┘ └────▲──────┘
         │             │           │            │
   luna-reflexiona ────┘    luna-explora ───────┘
   (resume, extrae creencias,  (elige interés por progreso de
    evoluciona el automodelo)   aprendizaje, consulta fuentes,
                                propone/corre simulaciones, escribe)
```

## Módulos

| Módulo | Archivo | Qué hace | Datos (en `~/.luna/`) |
|---|---|---|---|
| Constitución | `personality/constitucion.toml`, `src/ia/persona.py` | Principios estables con conductas "debe / nunca" | en el repo |
| Automodelo | `src/ia/persona.py`, `src/ia/reflection.py` | Intereses semilla, humor, bromas, opiniones; versionado | `automodelo.json`, `automodelo_historial.jsonl` |
| Memoria | `src/ia/memory.py` | Turnos de conversación y resúmenes, búsqueda de texto completo | `memoria.sqlite` |
| Creencias | `src/ia/beliefs.py` | Tripletas con nivel epistémico; reglas de cambio, refuerzo y desacuerdo | `creencias.sqlite` |
| Espacio de trabajo | `src/ia/workspace.py` | Competencia por un foco limitado; `/foco` para inspeccionarlo | (en memoria) |
| Intereses | `src/ia/agenda.py` | Curiosidad como progreso de aprendizaje, aburrimiento, crecimiento | `intereses.json` |
| Exploración | `src/ia/explore.py` | Sesión autónoma: fuentes → 5 niveles → simulación → cuaderno | `cuaderno.jsonl` |
| Reflexión | `src/ia/reflection.py` | Resúmenes, extracción de creencias, cambios al automodelo (máx. 3) | `reflexion.json` |
| Permisos | `src/ia/permissions.py` | 4 niveles en código, cola de propuestas | `permisos.toml`, `propuestas.jsonl`, `acciones.jsonl` |
| Herramientas | `src/ia/tools.py` | Wikipedia, arXiv (lectura), Python (simulación) | — |
| Crítico | `src/ia/critic.py` | Revisa respuestas contra las reglas "nunca"; juez de escenarios | — |
| Voz | `src/ia/voice.py` | Whisper (oír) + voz del sistema (hablar), sin probar aún | — |

## Decisiones clave

1. **Símbolos explícitos.** Principios, creencias, intereses y permisos son datos que
   se pueden leer, editar, contar y verificar. El modelo propone; las estructuras
   deciden lo que se guarda, lo que entra en el foco y lo que se permite.
2. **Seguridad en código, no en el prompt.** Un modelo sin censura puede pedir
   cualquier cosa; la política de permisos decide igual.
3. **Continuidad frente a transformación.** La constitución no la toca la reflexión; el
   automodelo cambia como máximo 3 cosas por reflexión, siempre con un motivo, y se
   puede revertir.
4. **Memoria frente a privacidad.** Todo es local; Usx puede buscar y borrar recuerdos.
   Las creencias guardan su fuente.
5. **Cada pieza se puede desactivar** para hacer ablaciones (`--foco 0`, `--critico`,
   `--seleccion aleatoria`, condiciones de E1).

## Límites conocidos de la v1

- La calidad depende mucho del modelo local (9B): extracción de creencias ruidosa, JSON
  a veces inválido (se registra y no rompe nada).
- La relevancia del foco y la novedad de los hallazgos usan solapamiento de palabras;
  los embeddings serían mejores (siguiente paso posible).
- El ejecutor de Python aísla fallos, pero no es un sandbox de seguridad.
- La voz no se ha probado con hardware real.
