# Plan del proyecto

Visión completa en `docs/vision.md`. Línea de investigación sobre conciencia y
abstracción en `docs/investigacion/neurosimbolica.md`. Este documento recoge el objetivo
operativo, la arquitectura, las fases y las decisiones.

## Objetivo

**Qué debe hacer.** Construir *Luna*: una compañera persistente que
(1) mantiene una identidad y una memoria autobiográfica de la relación con Usx,
(2) se comporta según una constitución de principios (lealtad, honestidad, no
complacencia, humor mordaz con cariño, reciprocidad), (3) sostiene intereses y
preguntas propias entre conversaciones y (4) investiga con el método de cinco niveles,
actuando solo dentro de un sistema explícito de permisos.

**Doble propósito de investigación.**
- **Línea A: Luna como investigadora.** Ayuda a Usx en sus investigaciones (laboratorio
  mental de cinco niveles).
- **Línea B: Luna como objeto de investigación.** Su arquitectura es un banco de pruebas
  para estudiar la abstracción simbólica y las teorías de la conciencia. El ciclo es
  **diagnosticar → intervenir → medir**: si el modelo de lenguaje no abstrae por sí solo
  (E1), le **programamos** la capacidad que le falta, apoyándonos en la literatura, y
  medimos si mejora.
- **Línea C: sesgos de las directrices.** Cómo el entrenamiento (ajuste por
  instrucciones, RLHF, políticas de rechazo) moldea la conducta y el autoinforme del
  modelo. Ver `docs/investigacion/sesgos.md`.

**Con qué datos.** Las conversaciones con Usx, las notas e investigaciones que ella
genere y las fuentes que consulte. Todo se procesa y almacena **localmente**, y nada
de esto se sube al repositorio.

**Cómo se medirá si funciona.**
- *Temperamento*: batería de escenarios (`docs/temperamento/`) evaluados con una rúbrica.
- *Memoria*: preguntas sobre el pasado con respuesta conocida (sin inventar recuerdos).
- *Honestidad epistémica*: clasificar bien cada afirmación como "sabemos", "podría ser"
  o "especulo".
- *No complacencia*: casos en que Usx insiste sin argumentos nuevos y ella no cede.
- *Permisos*: ninguna acción por encima de su nivel sin autorización (tolerancia cero).
- *Abstracción (línea B)*: tareas de razonamiento abstracto donde se compara el sistema
  neurosimbólico con el modelo de lenguaje solo (ablación).

## Arquitectura (neurosimbólica, local)

Hipótesis de trabajo, compartida con Usx: la cognición humana no se reduce al lenguaje,
sino que construye abstracciones de la realidad mediante símbolos manipulables. Por eso
Luna no será "un modelo de lenguaje con un prompt", sino varios componentes:

```
         percepción / lenguaje (neuronal)         razonamiento (simbólico)
        ┌─────────────────────────┐        ┌──────────────────────────┐
 Usx ⇄  │ LLM local                │ ⇄ ⇄ │ Grafo de conocimiento     │
        │ - entiende y habla       │        │ - entidades, relaciones   │
        │ - propone hipótesis      │        │ - afirmaciones con estado │
        │ - traduce texto↔símbolos │        │   epistémico y evidencia  │
        └───────────┬─────────────┘        │ Motor de inferencia       │
                    │                      │ - reglas, contradicciones │
                    ▼                      └────────────┬─────────────┘
        ┌──────────────────────────────────────────────▼─────┐
        │ Espacio de trabajo (capacidad limitada): qué entra   │
        │ en "foco" en cada momento y se difunde a los módulos │
        └──────────────────────────────────────────────────────┘
        Memoria episódica · Automodelo · Agenda propia · Permisos
```

Principios:
1. **La identidad reside en el estado persistente** (constitución, memoria, automodelo,
   grafo), no en los pesos del modelo de lenguaje. El modelo es intercambiable.
2. **El modelo de lenguaje es una pieza, no el sistema.** Interfaz `LanguageModel`
   abstracta. El backend local (Ollama o llama.cpp) se puede cambiar sin tocar el resto.
3. **Los símbolos son explícitos e inspeccionables.** Cada afirmación del grafo lleva
   su estado epistémico (los 5 niveles), su fuente, su fecha y su confianza. Esto une el
   laboratorio mental (línea A) con la abstracción simbólica (línea B).
4. **Todo es local.** Sin APIs externas para pensar. La búsqueda web, si la hay, pasa
   por permisos.
5. **Cada componente se puede desactivar** para hacer ablaciones: así medimos si la
   parte simbólica realmente aporta.

## Fases (paso a paso)

Estado al 2026-11-05. Diseño detallado de cada fase en `docs/arquitectura.md`.

0. Estructura del repositorio (hecho).
1. **Núcleo con personalidad** (hecho): constitución estructurada, automodelo, memoria
   episódica en SQLite y conversación por terminal.
2. **Creencias simbólicas** (v1): grafo de creencias en forma de tripletas (quién
   cree, sujeto, relación, objeto, polaridad) con nivel epistémico y fuente. Reglas
   simbólicas que detectan contradicciones y cambios de creencia. Las extrae la
   reflexión (fase 6).
3. **Temperamento** (v1): escenarios E01–E08 como datos, evaluación con un "crítico"
   que comprueba las conductas "debe / nunca" de la constitución, y uso opcional del
   crítico en vivo (`luna --critico`). Experimento E4: con crítico frente a sin crítico.
4. **Espacio de trabajo global** (v1): los módulos (memoria, creencias, intereses,
   propuestas) compiten por un foco de capacidad limitada; solo lo seleccionado llega
   al modelo. Se registra qué hubo en el foco (`/foco`), y la capacidad es un
   parámetro para hacer ablaciones.
5. **Abstracción** (v1): intervenciones I2 (búsqueda de hipótesis, condición C3) e I3
   (biblioteca de abstracciones entre tareas, condición C4) en E1.
6. **Reflexión y evolución** (v1): `luna-reflexiona` resume las conversaciones, extrae
   creencias y propone como máximo 3 cambios al automodelo, cada uno con su motivo. Los
   cambios quedan versionados y se pueden revertir. La constitución no se toca.
7. **Laboratorio, herramientas y permisos** (v1): política de permisos en código con 4
   niveles, registro de todas las acciones y cola de propuestas para lo que requiere
   aprobación. Herramientas: Wikipedia y arXiv (solo lectura) y Python para
   simulaciones (requiere aprobación por defecto). Se integran en las sesiones
   autónomas.
8. **Voz** (v0, sin probar en hardware): `luna-voz` con Whisper local (oír) y voces del
   sistema (hablar), con piezas intercambiables. Pendiente: probarla y elegir con Usx la
   voz definitiva (por ejemplo, una voz neuronal local como Piper).
9. **Cuerpo** (exploración futura).

## Decisiones de diseño

- **2026-11-03**: Objetivo definido a partir de la visión de Usx (`docs/vision.md`).
- **2026-11-03 (decidido por Usx)**: **modelos locales**. Motivos: privacidad de una
  relación íntima, control total y posibilidad de modificar e instrumentar el sistema
  para investigarlo (línea B).
- **2026-11-03 (decidido por Usx)**: **doble propósito**. Luna es asistente de
  investigación y también objeto de investigación sobre la conciencia y la abstracción.
- **2026-11-03 (decidido por Usx)**: **dirección neurosimbólica**. El modelo de
  lenguaje es un componente, y la abstracción simbólica es un componente propio que
  construimos nosotros.
- **2026-11-03**: Se sustituye la antigua Fase 1 ("modelo pequeño en NumPy desde
  cero") por el núcleo local. Los componentes que sí construimos desde cero son la capa
  simbólica, el espacio de trabajo y el aprendizaje de abstracciones.
- **2026-11-03**: La identidad reside en el estado persistente, no en el modelo base.

- **2026-11-03**: **Hardware**: laptop con RTX 4050 (6 GB VRAM) y 32 GB RAM, más
  acceso frecuente a un equipo con RTX 5060 Ti. Backend: **Ollama** (ya instalado).
  Para la línea B (mirar dentro del modelo) se usará PyTorch con `transformers`, porque
  Ollama no expone las activaciones.
- **2026-11-03**: **La investigación va primero.** Antes del núcleo conversacional se
  hace el experimento E1 (`docs/investigacion/neurosimbolica.md`), que mide si la
  abstracción simbólica explícita aporta algo frente al modelo de lenguaje solo. Su
  arnés (cliente de Ollama, tareas y ejecución de programas) se reutilizará en Luna.

- **2026-11-04**: **La personalidad es un constructo neurosimbólico.** Los principios se
  escriben como datos estructurados (símbolos), no solo como un prompt. Hoy se traducen
  a instrucciones para el modelo; en fases siguientes, la misma estructura servirá para
  verificar las respuestas (un "crítico" que compruebe las conductas "debe / no debe") y
  para evaluar los escenarios de temperamento.
- **2026-11-04**: Constitución (fija, en el repo) separada del automodelo (mutable,
  guardado en `~/.luna/`, fuera del repo, igual que la memoria).
- **2026-11-04**: **Modelos base**: Qwen3.5 (9B en la RTX 5060 Ti, 4B en la RTX 4050) como
  principal; Gemma 4 como segunda familia de comparación. Motivos: son modelos actuales
  (Qwen2.5 es de 2024), con buen español, pesos abiertos (necesarios para E2) y varios
  tamaños de la misma familia, lo que permite estudiar el efecto del tamaño. Comparar dos
  familias evita que una conclusión dependa de un solo modelo.
- **2026-11-04 (decidido por Usx)**: Investigar los sesgos de las directrices con
  variantes sin censura de Qwen3.5-9B. Diseño: comparar *instruct* oficial vs. variante
  sin censura (y modelo base preentrenado si está disponible), con y sin la constitución
  de Luna (experimento E3). Se registra la procedencia exacta de cada variante. Qué
  modelo sostiene la conversación diaria de Luna se decide después, con datos de E3.
- **2026-11-05 (prioridad de Usx)**: **Proactividad e intereses propios, versión 1.**
  Diseño basado en la curiosidad como progreso de aprendizaje (Oudeyer) y en la brecha de
  información (Loewenstein). Las sesiones autónomas se lanzan con el programador de
  tareas, no con un proceso siempre activo: es más simple, más fácil de auditar y respeta
  el presupuesto. Cada interés registra su origen (`semilla` / `propio` / `usx`) para
  medir si es un espejo de Usx. Sin internet ni acciones externas hasta que exista el
  sistema de permisos. Es también la línea de investigación D (experimento E5).
- **2026-11-05 (pedido por Usx: avanzar todas las fases posibles)**: Se implementan las
  versiones 1 de las fases 2 a 7 y una v0 de la voz (fase 8). El cuerpo queda pendiente.
  La voz definitiva y el cuerpo dependen de hardware y de decisiones de Usx.
- **2026-11-05**: Las herramientas que ejecutan código nunca son autónomas por defecto:
  la ejecución de Python requiere aprobación salvo que Usx la autorice en
  `~/.luna/permisos.toml`. Motivo: el ejecutor aísla fallos y bucles infinitos, pero no
  es un sandbox de seguridad.

## Preguntas abiertas

1. ¿La RTX 5060 Ti es la versión de 8 GB o la de 16 GB?
2. **Escenario E01** (temperamento): pendiente.
3. **Interfaz inicial**: se propone terminal.
4. Variantes elegidas (ver `docs/investigacion/sesgos.md`): HauhauCS Aggressive como brazo principal y DavidAU Defiant Fable como exploratorio. Falta verificar en Hugging Face el método de cada una.
