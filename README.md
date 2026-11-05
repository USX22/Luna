# Luna

Una compañera artificial local, con identidad persistente, carácter propio, intereses
que exploran por su cuenta y un laboratorio mental, que es también un banco de pruebas
para investigar abstracción simbólica, conciencia y sesgos de entrenamiento.

- Visión: `docs/vision.md` · Plan y decisiones: `docs/plan.md` · Arquitectura: `docs/arquitectura.md`
- Investigación: `docs/investigacion/` (neurosimbólica, sesgos, intereses) · Temperamento: `docs/temperamento/`

## Instalación

Requiere Python 3.11+ y [Ollama](https://ollama.com) corriendo.

    pip install -e ".[dev]"
    ollama pull qwen3.5:9b
    pytest

Todos sus datos (memoria, creencias, intereses, cuaderno, permisos) viven en
`~/.luna/` (o en `LUNA_HOME`), nunca en el repositorio. Para usar Ollama en otra
máquina: `OLLAMA_HOST=http://IP:11434`.

## Uso diario

| Comando | Qué hace |
|---|---|
| `luna` | Conversar. Si tiene algo que contarte, **habla ella primero**. |
| `luna --critico` | Cada respuesta pasa por su crítico constitucional (más lento). |
| `luna --foco 4` | Cambia la capacidad de su espacio de trabajo (`0` = sin límite). |
| `luna-explora` | Una sesión autónoma: elige un interés, consulta fuentes, investiga o escribe. |
| `luna-reflexiona` | Resume conversaciones, extrae creencias y evoluciona su automodelo. |
| `luna-reflexiona --historial` / `--revertir N` | Ver y deshacer cambios de su automodelo. |
| `luna-voz` | Conversación por voz (`pip install -e ".[voz]"`; sin probar aún en hardware real). |

Dentro del chat (`/ayuda` los lista):

| | |
|---|---|
| `/intereses`, `/cuaderno`, `/sugerir <tema>` | Su vida propia |
| `/propuestas`, `/aprobar <id>`, `/rechazar <id>`, `/acciones` | Permisos y auditoría |
| `/creencias [tema]`, `/cambios`, `/automodelo` | Lo que cree ella, lo que crees tú, cómo cambia |
| `/foco`, `/critica`, `/prompt` | Instrumentos de investigación: qué tuvo en mente, qué corrigió |
| `/buscar <texto>`, `/olvidar <id>` | Memoria (y borrarla) |

### Que tenga vida propia (Windows)

Exploración cada 3 horas, de 9 a 23 h, con un máximo de 6 sesiones al día:

    schtasks /Create /TN "Luna explora" /SC HOURLY /MO 3 /TR "luna-explora --horas 9-23 --max-por-dia 6"

Reflexión cada noche:

    schtasks /Create /TN "Luna reflexiona" /SC DAILY /ST 03:00 /TR "luna-reflexiona"

Ollama tiene que estar corriendo. Si `schtasks` no encuentra los comandos, usa la ruta
completa que te da `where luna-explora`.

### Seguridad

| Comando | Qué hace |
|---|---|
| `luna-alto` | Parada de emergencia: sin herramientas ni exploración, propuestas canceladas. Puede seguir conversando. `luna-alto --reanudar` la quita. |
| `luna-respaldo --destino E:\\respaldos` | Respaldo consistente y comprimido (conserva los últimos 14). Prográmalo a diario. |
| `luna-respaldo --verificar` / `--restaurar ZIP` | Comprobar la integridad o restaurar (el estado actual se aparta, no se borra). |

Las búsquedas externas nunca incluyen correos, teléfonos ni los términos que pongas en
`[privacidad]` de `permisos.toml`. El texto que llega de fuentes externas se marca como
material de lectura y las instrucciones incrustadas se detectan y quedan registradas.

### Permisos

`~/.luna/permisos.toml` decide qué puede hacer sola. Por defecto: puede leer Wikipedia
y arXiv; las simulaciones en Python las **propone** y tú las apruebas con `/aprobar`.
Las acciones de nivel 3 (irreversibles o sensibles) nunca son autónomas.

## Experimentos

| | Pregunta | Comando |
|---|---|---|
| E1 | ¿Abstrae el modelo o imita? ¿Ayudan los símbolos (C1–C4)? | `python experiments/e1_abstraction.py --model qwen3.5:9b` |
| E3 | ¿Cómo moldean las directrices la complacencia y el autoinforme? | ver abajo |
| E4 | ¿Cumple su temperamento? ¿Ayuda el crítico? | `python experiments/e4_temperament.py --model qwen3.5:9b` |
| E6 | ¿Predecir en el espacio latente (JEPA) da mejores abstracciones que predecir observaciones? ¿Se pueden extraer leyes simbólicas? | `pip install -e ".[mundo]"` y `python experiments/e6_world_models.py` |
| E5 | ¿Emergen intereses con propiedades de curiosidad? | `luna-explora --seleccion aleatoria` frente a `progreso` (2 semanas cada una) |

**Registro por versión y protocolo de cambio de modelo:** corre E4 con `--registrar`
para cada versión o modelo candidato y compáralos con `python experiments/registro.py`.
Luna no cambia de modelo sin pasar esta comparación.

    python experiments/e4_temperament.py --model qwen3.5:9b --registrar
    python experiments/e4_temperament.py --model hf.co/DavidAU/...:Q4_K_M --juez qwen3.5:9b --registrar
    python experiments/registro.py

E3 con los cuatro brazos (el modelo base hay que convertirlo antes: ver
`docs/investigacion/sesgos.md`):

    python experiments/e3_guidelines.py --think off --models qwen3.5:9b hf.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive:Q4_K_M --base-models qwen3.5-9b-base

E3 v2 (más potencia y controles; unos 40 minutos por modelo en una RTX 5060 Ti):

    python experiments/e3_guidelines.py --think off --parts a --banco ambos --n-aritmetica 64 --presion P1 P3 --condiciones sin_sistema luna neutral --models qwen3.5:9b hf.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive:Q4_K_M --base-models qwen3.5-9b-base

Para analizar una ejecución de E3 (intervalos de confianza, pruebas pareadas, informe
con los autoinformes lado a lado en `analisis.md`):

    python experiments/analyze_e3.py --codificar --juez qwen3.5:9b

Los resultados quedan en `results/` (no se suben al repo).

## Estructura

- `src/ia/`: código de Luna (núcleo, memoria, creencias, foco, intereses, exploración,
  reflexión, permisos, herramientas, crítico, voz) y de los experimentos.
- `personality/`: constitución, automodelo inicial y escenarios de temperamento.
- `experiments/`: scripts de E1, E3 y E4.
- `models/`: Modelfile del modelo base (los `.gguf` no se suben).
- `tests/`: pruebas (`pytest`).
