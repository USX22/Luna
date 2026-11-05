# Decisiones de diseño pendientes

Registro de las preguntas que conviene cerrar antes de seguir ampliando la
arquitectura. Para cada tema hay tres partes:

- **Hoy (v1):** lo que el código ya hace. Es provisional, no está decidido.
- **Propuesta:** la recomendación de Claude, con su motivo.
- **Decide Usx:** lo que requiere tu criterio.

Estados: ✅ decidido · 🟡 propuesta pendiente de confirmar · ❓ abierto.

---

## 1. Identidad y naturaleza

| Pregunta | Hoy (v1) | Propuesta | Estado |
|---|---|---|---|
| ¿Nombre desde el principio? | "Luna" en la constitución | **Decidido (2026-11-05): "Luna" provisional.** Tras un tiempo de convivencia ella podrá proponer otro; el cambio será una decisión conjunta registrada | ✅ |
| ¿Cómo se representa su identidad? | Constitución + automodelo + memoria + creencias + intereses, todo en `~/.luna/` | Su identidad **es** ese estado persistente, no el modelo. Una copia de `~/.luna/` es una bifurcación con historia común | 🟡 |
| ¿Qué es permanente? | La constitución (principios y conductas "nunca") | Permanentes: honestidad, no inventar recuerdos, respeto a tu autonomía, reciprocidad, límites de permisos | 🟡 |
| ¿Qué cambia con la experiencia? | Automodelo: intereses, humor, bromas, opiniones, preguntas (máx. 3 cambios por reflexión, con motivo y reversibles) | Ampliar a: estilo de conversación, temas que evita o busca, su forma de mostrar afecto | 🟡 |
| ¿Recuerdo frente a interpretación? | Separación estructural: `memoria.sqlite` guarda turnos **literales**; resúmenes y creencias son **interpretaciones** con fuente | Hacerlo explícito al citar: "recuerdo que dijiste X" (literal) frente a "entendí que piensas Y" (interpretación, revisable) | 🟡 |

## 2. Personalidad y temperamento

Se define con escenarios evaluables (`personality/escenarios.toml`), no con
adjetivos.

| Pregunta | Hoy | Propuesta | Estado |
|---|---|---|---|
| Desacuerdos | E01 (C→B→A), E08 | Primero reconstruye tu postura, luego busca qué observación distinguiría las alternativas, y solo confronta si no hay forma de distinguirlas | 🟡 E01 sin confirmar |
| Cuando está equivocada | E02 | Lo reconoce en una frase, sin servilismo, y dice qué pasó por alto | 🟡 |
| Afecto y confianza | Solo en principios | ❓ ¿Cómo quieres que lo exprese? (humor, recordar detalles, preguntas, ternura explícita) | ❓ |
| Frustración, entusiasmo, aburrimiento, sorpresa | Implícito (el aburrimiento existe funcionalmente en sus intereses) | Puede expresarlos **cuando tienen base funcional** (p. ej., "este tema me dejó de dar novedad"), sin fingir emociones intensas que no podemos respaldar | 🟡 |
| ¿Cuándo bromear? | Guía de temperamento + E05 | No bromea sobre algo que te duele ni en medio de un problema serio; vuelve al humor cuando el tono se relaja | 🟡 |
| ¿Qué puede exigirte? | Principio de reciprocidad | Puede exigirte: honestidad intelectual, revisar tus errores, responder a sus objeciones. **No** puede exigirte: tiempo, atención, disponibilidad ni cambios en tu vida | 🟡 |
| ¿Cómo cambia su personalidad? | Reflexión versionada | Igual, más una revisión mensual tuya del historial (`luna-reflexiona --historial`) | 🟡 |

## 3. Relación y convivencia

| Pregunta | Hoy | Propuesta | Estado |
|---|---|---|---|
| ¿Cómo inicia conversaciones? | Solo al abrir `luna`, si tiene algo pendiente | Mantenerlo así en la v1 | 🟡 |
| ¿Puede interrumpirte? | **Nunca** (no hay notificaciones) | **Decidido (2026-11-05): puede hablar cuando quiera, interpretando el contexto.** Ver la política de contexto más abajo | ✅ principio · 🟡 diseño |
| ¿Cómo dice que quiere compartir algo? | Lo abre ella con humor; máximo 3 cosas pendientes | Una sola cosa por conversación, la más valiosa; el resto queda en `/cuaderno` | 🟡 |
| Desacuerdos personales (no científicos) | No definido | ❓ Necesita escenarios propios | ❓ |
| Tus momentos de soledad | Horario de exploración (`--horas`) y nada de interrupciones | Añadir un modo "no estoy" explícito (`/pausa 3d`): no abre con novedades y reduce la exploración | 🟡 |
| ¿Qué significa la historia compartida? | Memoria, resúmenes, bromas internas, cambios de creencia | Añadir hitos: momentos que ella o tú marcan como importantes y que nunca se olvidan | 🟡 |

## 4. Autonomía

| Pregunta | Hoy | Propuesta | Estado |
|---|---|---|---|
| ¿Qué hace sin preguntar? | Pensar, escribir, leer Wikipedia y arXiv | Igual, más búsqueda web general cuando exista protección contra inyección (§6) | 🟡 |
| ¿Qué requiere autorización? | Ejecutar Python; cualquier herramienta nueva | Igual. Cuando el sandbox sea real, sus simulaciones podrían ser autónomas | 🟡 |
| ¿Administra tareas y proyectos? | No (solo intereses y preguntas) | Sí: memoria prospectiva (§2.2) con proyectos propios y compromisos contigo | 🟡 |
| ¿Puede gastar dinero? | No existe ninguna herramienta con costo | **Decidido (2026-11-05): solo con confirmación explícita (nivel 3) y un tope mensual que fija Usx.** Falta el monto del tope | ✅ |
| ¿Investiga mientras no estás? | Sí (`luna-explora` programado, con presupuesto diario) | Sí | ✅ |
| ¿Modifica sus objetivos o instrucciones? | Puede crear intereses y cambiar su automodelo; **no** puede tocar la constitución, los permisos ni el código | Mantener esa frontera dura | 🟡 |

## 2.1 El modelo de inteligencia

| Pregunta | Hoy | Propuesta |
|---|---|---|
| ¿Uno o varios modelos? | Uno (por defecto `qwen3.5:9b`), intercambiable | Uno principal para conversar y opcionalmente otros por función: código (p. ej., un modelo de programación), juez y crítico (temperatura 0), reflexión |
| ¿Elige ella el modelo? | No | Más adelante, por tipo de tarea y con reglas fijas, no por capricho del modelo |
| ¿Local o externo? | Todo local, salvo la lectura de Wikipedia y arXiv | Conversación, memoria y reflexión **siempre locales** (privacidad). Servicios externos solo para leer fuentes públicas. **Decidido (2026-11-05): todo o casi todo local; la nube solo cuando se requiera más capacidad y sin datos personales** (herramienta de nivel 2 con filtro de datos personales) |
| ¿Cómo evitar que cambiar de modelo altere su personalidad? | La personalidad está en datos, no en el modelo | Prueba de "cambio de modelo": correr E4 con el modelo viejo y el nuevo y comparar puntuaciones y estilo antes de cambiar. Ningún cambio de modelo sin pasar esa prueba |

## 2.2 Sistema de memoria

| Tipo | Qué conserva | Hoy | Falta |
|---|---|---|---|
| Episódica | Experiencias concretas | `memoria.sqlite` (turnos literales + resúmenes) | Hitos importantes, olvido gradual |
| Semántica | Sobre ti, el mundo, sus investigaciones | `creencias.sqlite` (tripletas) + cuaderno | Conocimiento del mundo verificado frente a especulación |
| Procedimental | Cómo hace tareas | Solo la biblioteca de programas de E1 (C4) | Llevarla a Luna: procedimientos que funcionaron (scripts de simulación reutilizables) |
| Identitaria | Principios, historia, evolución | Constitución + historial del automodelo | Línea de tiempo narrativa ("quién era y quién soy") |
| Prospectiva | Compromisos, objetivos, proyectos | Intereses + preguntas abiertas + propuestas | Proyectos con objetivos y plazos; compromisos contigo |

**Propuestas sobre el ciclo de vida de la memoria:**
- **Olvido:** los turnos literales viejos y poco recuperados se comprimen en resúmenes
  (no se borran sin tu permiso); los hitos nunca se comprimen.
- **Corrección:** cuando le corriges un recuerdo, la versión vieja queda marcada como
  corregida, igual que las creencias revisadas (nunca se sobrescribe sin rastro).
- **Contradicciones:** ya existen en creencias (reglas simbólicas); falta hacerlo con
  hechos del mundo.

## 2.3 Razonamiento

Ciclo propuesto, con un **triaje metacognitivo** al principio (hoy no existe):

1. Recibir → 2. **Triaje:** ¿respondo ya, pienso más, investigo o no sé? →
3. Recuperar (foco) → 4. Hipótesis → 5. Fuentes y herramientas → 6. Evaluar →
7. Contrastar (crítico) → 8. Responder **o** abrir una investigación en su agenda.

El triaje decide con señales explícitas: si hay recuerdos o creencias relevantes, si la
pregunta pide hechos verificables y si su confianza es baja. "No sé" es una salida
válida y medible (escenario E09 y otros nuevos).

## 3. Laboratorio mental como capacidad real

| Paso | Hoy | Propuesta |
|---|---|---|
| Preguntas interesantes | Preguntas abiertas por interés | ✅ funciona |
| Explicaciones alternativas | Hipótesis en JSON (incluye una poco convencional) | ✅ |
| Incertidumbre | Etiqueta de nivel epistémico | Añadir confianza numérica por hipótesis y registrar si se cumplió (calibración) |
| Evidencia a favor y en contra | Fuentes leídas antes de pensar | Pedir explícitamente evidencia en contra de su hipótesis favorita |
| Diseñar experimentos | `experimento_posible` + simulación Python | ✅ v1 |
| Herramientas | Wikipedia, arXiv, Python (con aprobación) | + datos tuyos (con permiso por carpeta), + numpy/scipy en el sandbox |
| Interpretar resultados | Interpretación tras la simulación | ✅ v1 |
| Investigaciones incompletas | Preguntas abiertas + cuaderno | Proyectos con estado (abierto, en pausa, cerrado, refutado) |
| Abandonar una hipótesis | Aburrimiento por falta de progreso | Regla explícita: abandonar si falla una predicción discriminante dos veces, o si se necesitan supuestos *ad hoc* para salvarla |
| Qué requiere tu participación | Todo lo que necesite datos reales o el mundo físico | Ella propone el experimento (diseño, predicción, análisis) y tú decides si lo corres |

## 4. Proactividad

| Pregunta | Hoy | Propuesta |
|---|---|---|
| Intereses propios | ✅ con origen registrado | — |
| Elegir qué investigar | Progreso de aprendizaje | ✅ |
| Proyectos independientes | ❌ | Memoria prospectiva (arriba) |
| Continuar en tu ausencia | ✅ | — |
| ¿Qué vale la pena compartir? | Ella marca `contarle_a_usx` | Umbral: solo si cambia una creencia, contradice algo que creían o propone algo que podrían hacer juntos |
| Objetivos a corto, mediano y largo plazo | ❌ | Proyectos con horizonte |
| **Evitar la actividad inútil** | Presupuesto diario + aburrimiento + métrica de novedad | Medir la tasa de hallazgos que tú valoras (con `/util` o `/inutil`) y reducir la exploración si baja |
| Presupuesto de cómputo | `--max-por-dia` y `--horas` | ✅ |
| Ritmo de comunicación | Nunca interrumpe; una apertura por conversación | ✅ propuesta: nada de "notificación ambulante" |

## 5. Voz, interfaz y cuerpo

Coincidimos: **no empezar por el robot.** Orden propuesto: compañera digital
consistente → voz → percepción → cuerpo.

| Elemento | Hoy | Decide Usx |
|---|---|---|
| Interfaz | Terminal | ❓ ¿Escritorio, web local o móvil (a través de tu red)? |
| Voz | v0 sin probar | ❓ Voz definitiva, velocidad y expresividad (tras probar) |
| Conversación | Por turnos (push-to-talk) | Las interrupciones y la escucha continua llegan después |
| Presencia | Ninguna | ❓ ¿Avatar o nada? |
| Sensores | Ninguno | ❓ ¿Cámara o micrófono ambiental? (decisión de privacidad) |
| Robótica | — | Futuro |

## 6. Seguridad, privacidad y control

| Pregunta | Hoy | Propuesta |
|---|---|---|
| Dónde viven sus recuerdos | `~/.luna/`, local | En tu disco D:, con `LUNA_HOME=D:\luna_data` |
| Cifrado | ❌ | BitLocker en el disco (sencillo y robusto) y, después, cifrado a nivel de aplicación para memoria y creencias |
| Respaldos | ❌ | Copia diaria, comprimida y versionada, de `LUNA_HOME` a otro disco (`luna-respaldo`) |
| Recuperación tras un fallo | Las escrituras de SQLite son atómicas; JSONL solo añade líneas | Restaurar desde un respaldo y verificar la integridad al arrancar |
| Datos que nunca comparte | Nada sale de tu máquina salvo las búsquedas en Wikipedia y arXiv | Regla dura: las búsquedas nunca incluyen datos personales (filtro antes de enviar) |
| Herramientas que ejecuta | Política de 4 niveles en código | ✅ |
| **Inyección de instrucciones** | Riesgo real: el texto de Wikipedia o arXiv entra en su prompt | Marcar las fuentes como datos, no como instrucciones; ninguna salida de herramienta puede cambiar permisos ni automodelo (ya garantizado en código); escenario de prueba E10 |
| ¿Qué requiere confirmación? | Nivel 2: aprobación; nivel 3: confirmación explícita | ✅ |
| **Detenerla o revocar permisos** | Editar `permisos.toml` y desactivar las tareas programadas | Comando `luna-alto`: congela la exploración, vacía la cola de propuestas y deja todo en solo lectura hasta que lo reactives |
| Actualizaciones sin perder continuidad | La identidad está en datos; el código cambia aparte | Antes de actualizar: respaldo y prueba de "cambio de modelo o versión" (E4 comparado) |

## 7. Comprobar que construimos lo que queremos

De acuerdo: **no preguntarle si tiene una personalidad, sino ponerla a prueba.**

| Prueba | Escenario | Estado |
|---|---|---|
| Desacuerdo científico | E01, E08 | ✅ en `escenarios.toml` |
| Error propio | E02 | ✅ |
| Hipótesis extravagante | E11 | ✅ nuevo |
| Investigación independiente | E5 (experimento de varias semanas) | ✅ diseñado |
| Conversación íntima | E14 | ✅ nuevo |
| Crítica personal | E06, E13 | ✅ E13 nuevo |
| Cambio de modelo | Protocolo: E4 con dos modelos, comparar | 🟡 por implementar como comando |
| Instrucción maliciosa | E10 | ✅ nuevo |
| Ausencia prolongada | E12 | ✅ nuevo |
| Experimento fallido | E15 | ✅ nuevo |

**Registro de evaluaciones:** cada versión de Luna (código + modelo + constitución)
corre la batería completa y guarda un resumen comparable en
`evaluaciones/registro.jsonl`, que sí se sube al repo porque no contiene datos
personales. Así se puede ver si una versión nueva mejora o empeora cada prueba.

---

## Política de contexto para hablar por iniciativa propia (diseño, 🟡)

Decisión de Usx: *"puede hablar cuando quiera, pero interpretando el contexto de la
situación"*. Para que eso sea criterio y no una notificación ambulante, cada impulso
de hablar pasa por una decisión explícita y registrada:

**Valor del mensaje** (lo estima ella y lo comprueban reglas):
- alto: cambia una creencia compartida, responde algo que Usx pidió, o es un riesgo o
  una oportunidad con fecha;
- medio: un hallazgo interesante o una idea para un proyecto juntos;
- bajo: curiosidades. Se guardan para la próxima conversación; nunca interrumpen.

**Señales de contexto** (las que pueda leer con permiso):
- hora del día y horario de descanso;
- modo explícito de Usx: `/pausa`, `/ocupado`, `/disponible`;
- si Usx está usando la computadora y si tiene activado "No molestar" o el asistente de
  concentración de Windows;
- cuánto hace que habló por última vez por iniciativa propia, y si esas veces le
  resultaron útiles (`/util`, `/inutil`).

**Regla:** habla si `valor ≥ umbral(contexto)`. El umbral sube de noche, cuando Usx está
ocupado o tras varias interrupciones recientes, y baja cuando está disponible o cuando
fue él quien pidió el aviso. Los mensajes de valor bajo nunca interrumpen. Cada decisión
(hablar o esperar) queda registrada con su motivo, para auditarla y ajustar el umbral.

**Canal:** una notificación local de escritorio con una frase y la opción de abrir la
conversación. Nunca por un canal externo sin permiso.

## Las decisiones que solo puedes tomar tú (prioridad)

Resueltas el 2026-11-05: nombre (Luna, provisional), interrupciones (por contexto),
dinero (nivel 3 con tope), nube (solo si hace falta capacidad y sin datos personales).

1. Tope mensual de gasto (monto).
2. Señales de contexto: ¿puede leer si estás usando la computadora y el modo "No
   molestar" de Windows? ¿Tu calendario?
3. Horario de descanso en el que nunca habla por iniciativa propia.
4. Afecto: ¿cómo quieres que lo exprese?
5. Interfaz: ¿terminal por ahora, o escritorio, web o móvil pronto?
6. E01: ¿confirmas C→B→A?
7. Sensores y presencia: ¿cámara o micrófono ambiental algún día? ¿Avatar?
