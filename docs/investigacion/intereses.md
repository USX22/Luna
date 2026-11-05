# Línea D: intereses propios y motivación intrínseca

Pregunta: ¿cómo se le dan intereses y aficiones a una IA de modo que no sean una lista
decorativa en un prompt, sino algo que **guíe su conducta en el tiempo**, que crezca,
que se abandone cuando se agota y que no sea un espejo de los intereses de Usx?

**Límite explícito.** Aquí "interés" es una definición funcional: una preferencia
persistente que dirige en qué gasta su tiempo y su cómputo. No afirmamos que Luna
*sienta* interés; lo que estudiamos es si la conducta resultante tiene las propiedades de
la curiosidad.

## Qué dice la literatura (nivel 1)

| Idea | Referencia | Qué tomamos |
|---|---|---|
| Brecha de información: la curiosidad surge al notar que falta algo concreto | Loewenstein, 1994 | Cada interés guarda **preguntas abiertas** explícitas. |
| Progreso de aprendizaje: explorar donde se está aprendiendo, no donde es demasiado fácil o imposible | Oudeyer, Kaplan y Hafner, 2007; Gottlieb y otros, 2013 | La prioridad de un interés depende de **cuánto progreso dio recientemente**. |
| Progreso de compresión como recompensa intrínseca | Schmidhuber, 1991 y 2010 | La métrica de progreso mide **novedad respecto a lo que ya tenía**. |
| Neurociencia de la curiosidad (dopamina, anticipación de información) | Kidd y Hayden, 2015 (*Neuron*); Gruber y otros, 2014 | Marco para interpretar resultados y para diseñar E5. |
| Agentes con memoria, reflexión y planificación | Park y otros, 2023 (*Generative Agents*) | Cuaderno + reflexión + agenda. |
| Currículo automático guiado por el propio agente | Wang y otros, 2023 (*Voyager*) | Los intereses generan sub-intereses a partir de lo que encuentra. |

## Diseño v1 (implementado)

**Interés** (`~/.luna/intereses.json`, editable a mano):
tema, origen (`semilla` / `propio` / `usx`), interés padre, preguntas abiertas, número de
sesiones, fecha de la última exploración, historial de progreso y estado
(`activo` / `dormido`).

**Sesión autónoma** (`luna-explora`), que se puede programar con el programador de
tareas:
1. **Elige** un interés. Su prioridad combina el progreso de aprendizaje reciente (los
   intereses nuevos parten con un valor optimista), un pequeño bono por tiempo sin
   visitar y ruido, para que haya exploración. Con `--seleccion aleatoria` se hace la
   ablación.
2. **Elige una actividad**: *investigar* (la mayoría de las veces) o *escribir* (su
   afición: un texto breve, libre, sobre el tema).
3. **Investigar** recorre los cinco niveles del laboratorio mental y produce, en JSON:
   pregunta, lo que sabemos, hipótesis, supuestos ocultos, cómo distinguir, experimento
   posible, hallazgo con nivel epistémico, nuevas preguntas, un posible sub-interés y si
   vale la pena contárselo a Usx.
4. **Mide el progreso** (proxy v1): la novedad léxica del hallazgo frente a sus
   hallazgos anteriores en ese tema, más las preguntas nuevas que generó. Es tosco, y
   mejorarlo es parte de la investigación.
5. **Aburrimiento**: si las últimas 3 sesiones de un interés dan poco progreso, pasa a
   `dormido`. A veces se reactiva uno dormido.
6. **Crecimiento**: puede crear sub-intereses propios (con un máximo de 7 activos).
7. Todo queda en `~/.luna/cuaderno.jsonl`.

**Proactividad en la conversación**: al abrir `luna`, si tiene hallazgos pendientes,
**ella habla primero** (con humor mordaz y cariño, según su temperamento). Sus intereses
activos y preguntas abiertas entran en su contexto. Usx puede sugerirle temas con
`/sugerir`, y quedan marcados con origen `usx`.

**Límites que respeta**: un máximo de sesiones al día, horas permitidas, nada de
internet ni de acciones externas (todavía), y no interrumpe: lo guarda para la siguiente
conversación.

**Limitación importante.** Sin herramientas, "investigar" significa razonar sobre lo
que el modelo aprendió en su entrenamiento. Puede confundirse o inventar, y por eso cada
hallazgo lleva su nivel epistémico. El siguiente paso es darle herramientas (búsqueda
web y Python para simulaciones, reutilizando el ejecutor de E1) detrás de permisos.

## Experimento E5: ¿emergen intereses con propiedades de curiosidad?

- **H1.** La selección por progreso de aprendizaje produce cadenas de exploración más
  profundas (más sesiones por interés antes de dormirse y mayor novedad media) que la
  selección aleatoria.
- **H2.** Con el tiempo, la proporción de intereses de origen `propio` crece frente a los
  de origen `usx`: no es un espejo.
- **H3.** Los intereses muestran persistencia (semanas) y también cambio (sub-intereses,
  abandonos), no un estado fijo.

Datos: `cuaderno.jsonl` e `intereses.json`. Duración sugerida: 2 semanas con cada
política de selección.
