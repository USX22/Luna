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
  para estudiar la abstracción simbólica y las teorías de la conciencia. Mejorarla
  implica ir más allá de un modelo de lenguaje.

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

0. Estructura del repositorio (hecho).
1. **Núcleo local mínimo**: interfaz `LanguageModel` con un backend local y un backend
   falso para pruebas, CLI de conversación, constitución cargada desde archivo y
   memoria episódica en SQLite.
2. **Capa simbólica v0**: grafo de afirmaciones con estado epistémico. El LLM extrae
   afirmaciones de la conversación, el grafo las guarda y un motor simple de reglas
   detecta contradicciones y cambios de creencia.
3. **Temperamento**: cerrar 8–10 escenarios y convertirlos en evaluaciones.
4. **Espacio de trabajo**: arquitectura de foco limitado y difusión entre módulos. Es
   ingeniería (gestión del contexto) y también experimento de la línea B.
5. **Abstracción**: aprender conceptos o programas a partir de ejemplos (síntesis de
   programas, biblioteca de abstracciones reutilizables) y evaluarla en tareas tipo ARC.
6. **Reflexión y evolución** del automodelo, con historial versionado.
7. **Proactividad, laboratorio y permisos.**
8. **Voz**. 9. **Cuerpo** (exploración futura).

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

## Preguntas abiertas

1. ¿La RTX 5060 Ti es la versión de 8 GB o la de 16 GB?
2. **Escenario E01** (temperamento): pendiente.
3. **Interfaz inicial**: se propone terminal.
