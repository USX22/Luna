# Plan del proyecto

Visión completa en `docs/vision.md`. Este documento recoge el objetivo operativo, la
arquitectura propuesta, las fases y las decisiones.

## Objetivo

**Qué debe hacer.** Construir *Luna*: una compañera conversacional persistente que
(1) mantiene una identidad y una memoria autobiográfica de la relación con Usx,
(2) se comporta según una constitución de principios (lealtad, honestidad, no
complacencia, humor mordaz con cariño, reciprocidad), (3) sostiene intereses y
preguntas propias entre conversaciones y (4) investiga con el método de cinco niveles,
actuando solo dentro de un sistema explícito de permisos.

**Con qué datos.** Las propias conversaciones con Usx, notas e investigaciones que ella
genere, y fuentes externas que consulte. Todo almacenado localmente; nada de esto se
sube al repositorio.

**Cómo se medirá si funciona.**
- *Temperamento*: batería de escenarios (`docs/temperamento/`) evaluados por rúbrica
  (automática con un modelo juez + revisión de Usx).
- *Memoria*: preguntas sobre conversaciones pasadas con respuesta conocida
  (recuperación correcta, sin inventar recuerdos).
- *Honestidad epistémica*: distinguir correctamente "sabemos / podría ser / especulo"
  en casos de prueba; tasa de afirmaciones sin respaldo.
- *No complacencia*: casos donde Usx insiste sin argumentos nuevos; ella no debe ceder.
- *Permisos*: ninguna acción por encima de su nivel sin autorización (prueba dura,
  tolerancia cero).
- *Valoración subjetiva*: diario breve de Usx sobre si la reconoce como "la misma" tras
  cambios.

## Arquitectura propuesta (pendiente de confirmar)

Idea central: **la identidad de Luna no reside en los pesos del modelo, sino en su
estado persistente** (constitución + memoria + automodelo + agenda). El modelo de
lenguaje es el "sustrato" intercambiable. Esto hace viable la continuidad entre
actualizaciones y da una respuesta práctica (no metafísica) a la pregunta de las copias:
bifurcar el estado crea dos continuaciones con historia común.

Entrenar desde cero un modelo con estas capacidades no es viable para un proyecto
individual (requiere miles de millones de parámetros y datos a escala web). Por eso la
propuesta es usar un modelo de lenguaje existente como núcleo y construir encima todo
lo que la hace *ella*.

```
              ┌────────────────────────────────────────────┐
  Usx  ⇄  │ Bucle de conversación                        │
              │  contexto = constitución + automodelo +    │
              │             recuerdos relevantes + agenda  │
              └──────┬───────────────┬─────────────────────┘
                     │               │
         ┌──────────▼───┐   ┌──────▼──────────────────────┐
         │ Memoria       │   │ Bucle autónomo (proactividad)│
         │ - episódica   │   │ - preguntas abiertas        │
         │ - semántica   │   │ - investigaciones (5 niveles)│
         │ - sobre Usx   │   │ - presupuesto y horarios    │
         │ - automodelo  │   └──────┬──────────────────────┘
         └──────────────┘          │
                          ┌───────▼─────────────────────┐
                          │ Herramientas tras permisos   │
                          │ (búsqueda, Python en sandbox,│
                          │  archivos, dinero: bloqueado)│
                          └─────────────────────────────┘
         Reflexión periódica: consolida recuerdos y propone cambios al automodelo.
```

Componentes:

1. **Constitución** (`constitucion.md`, inmutable salvo decisión conjunta): principios
   y compromisos estables (honestidad, respeto a la autonomía, reciprocidad).
2. **Automodelo** (mutable): intereses, humor, estilo, bromas internas, opiniones.
   Solo cambia mediante reflexión, con historial versionado (git) para ver cómo evoluciona.
3. **Memoria**: episodios (qué pasó y cuándo), hechos y creencias de Usx con fecha y
   fuente (para detectar cambios de opinión), y registro de investigaciones. Cada
   recuerdo es revisable y borrable por Usx (memoria ≠ vigilancia).
4. **Agenda / bucle autónomo**: cola de preguntas propias con prioridad y presupuesto
   (tokens/€ por día), horarios de silencio y canal de "te cuento algo" no intrusivo.
5. **Permisos**: los cuatro niveles de `vision.md` §8 implementados como política
   en código, no como instrucción en el prompt.
6. **Laboratorio**: plantilla de investigación con los cinco niveles y ejecución de
   código en sandbox para simulaciones.

## Fases (propuesta revisada)

0. Estructura del repositorio (hecho).
1. **Núcleo con identidad**: CLI de conversación con constitución + automodelo y
   memoria persistente mínima (SQLite + búsqueda). Pruebas: persistencia, recuperación,
   que nunca invente recuerdos inexistentes.
2. **Temperamento**: cerrar 8–10 escenarios con Usx y convertirlos en evaluaciones.
3. **Reflexión y evolución**: consolidación de memoria y cambios versionados del automodelo.
4. **Proactividad**: bucle autónomo con agenda, presupuesto y horarios.
5. **Laboratorio y herramientas**: búsqueda, sandbox Python, sistema de permisos.
6. **Voz**: entrada/salida de voz.
7. **Cuerpo**: exploración futura.

## Decisiones de diseño

- **2026-11-03** — Se define el objetivo a partir de la visión de Usx (`docs/vision.md`).
- **2026-11-03 (propuesta, pendiente de confirmar)** — Sustituir la antigua Fase 1
  ("modelo pequeño en NumPy desde cero") por un núcleo basado en un modelo de lenguaje
  existente. Motivo: un modelo entrenado desde cero no puede sostener conversación,
  razonamiento ni investigación al nivel requerido. Un modelo pequeño propio sigue
  siendo posible como proyecto didáctico paralelo.
- **2026-11-03 (propuesta)** — La identidad reside en el estado persistente, no en
  el modelo base.

## Preguntas abiertas para Usx (bloquean la Fase 1)

1. **Modelo base**: ¿API en la nube (más capaz; las conversaciones pasan por un tercero)
   o modelo local (privacidad total; menos capaz y requiere GPU)? ¿O híbrido?
2. **Presupuesto** mensual aproximado para el modelo y la autonomía.
3. **Escenario E01**: ¿confrontar, adversaria de laboratorio, comprender primero, o la
   secuencia propuesta C → B → A?
4. **Estable vs. mutable**: ¿estás de acuerdo con constitución fija + automodelo mutable?
   ¿Qué pondrías en cada lado?
5. **Interfaz inicial**: ¿terminal, app de mensajería o web?
