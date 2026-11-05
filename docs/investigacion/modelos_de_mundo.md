# Línea E: modelos de mundo, razonamiento abstracto, JEPA y neurosimbolismo

## La tesis de Usx

> El giro actual hacia el razonamiento abstracto y los "modelos de mundo" es, en la
> práctica, una capitulación hacia los objetivos fundamentales del neurosimbolismo y de
> JEPA.

Es decir: después de apostar a que la predicción del siguiente token bastaría, el campo
está aceptando lo que el neurosimbolismo (Marcus; Garcez y Lamb) y la propuesta de
LeCun (JEPA) sostenían desde el principio. Hace falta representar el mundo de forma
abstracta, predecir en ese espacio y razonar sobre él, no solo sobre texto.

## Marco teórico (nivel 1: lo que sabemos)

| Idea | Referencias | Qué afirma |
|---|---|---|
| Modelos mentales | Craik, 1943 | La mente construye un "modelo a escala" de la realidad y lo usa para anticipar. |
| Codificación predictiva | Rao y Ballard, 1999; Friston (energía libre) | El cerebro predice sus entradas y aprende de los errores de predicción. Es el puente con la neurociencia de Usx. |
| Modelos de mundo aprendidos | Ha y Schmidhuber, 2018 | Un agente aprende un modelo latente del entorno y puede "soñar" y planificar en él. |
| JEPA | LeCun, 2022 (*A Path Towards Autonomous Machine Intelligence*); I-JEPA (Assran y otros, 2023); V-JEPA (Bardes y otros, 2024); V-JEPA 2 (Meta, 2025) | Predecir en el **espacio de representaciones**, no en el de observaciones (píxeles o tokens). Así el modelo puede ignorar los detalles impredecibles e irrelevantes. Exige evitar el **colapso** de las representaciones (con un codificador objetivo EMA o regularización de varianza, como VICReg). |
| Neurosimbolismo | Marcus, 2020; Garcez y Lamb, 2023 | Combinar aprendizaje neuronal con símbolos explícitos, composicionales y manipulables por reglas. |
| Medida de la abstracción | Chollet, 2019 (ARC) | La inteligencia es eficiencia en adquirir habilidades nuevas, no rendimiento en tareas vistas. |
| JEPA en señales biomédicas | Brain-JEPA (fMRI, 2024); ECG-JEPA (2024) *(verificar las referencias exactas)* | Aplicaciones que conectan directamente con el área de Usx. |

## Evaluación crítica de la tesis (nivel 2: lo que podría ser)

**A favor de la "capitulación":**
- Los sistemas actuales más capaces ya no son "solo un LLM". Usan razonamiento
  explícito en varios pasos, ejecución de código, herramientas, recuperación de
  información y verificación. Esa arquitectura es neurosimbólica **a nivel de sistema**.
- El interés industrial por los modelos de mundo (vídeo, robótica, planificación)
  reconoce que el texto no basta para anclar el conocimiento físico.
- Nuestro propio E1, con programas y verificación, va en esa dirección.

**En contra, o matices importantes:**
1. **Neurosimbolismo y JEPA no son el mismo programa.** JEPA es neuronal de extremo a
   extremo: sus "abstracciones" son vectores latentes, no símbolos. LeCun es escéptico de
   la manipulación simbólica explícita. Coinciden en el *objetivo* (modelo del mundo,
   abstracción, planificación) y discrepan en el *sustrato*. Si el campo "capitula",
   habría que precisar ante cuál de los dos. Esta tensión se puede investigar
   empíricamente, y Luna tiene los dos sustratos: el grafo de creencias y los programas
   son simbólicos, y un JEPA sería latente.
2. **Los LLM también desarrollan modelos de mundo internos.** Othello-GPT (Li y otros,
   2023; Nanda y otros, 2023) representa el tablero aunque solo vio jugadas. Gurnee y
   Tegmark (2023) encontraron representaciones lineales de espacio y tiempo. La
   predicción del siguiente token puede *producir* modelos de mundo, así que la pregunta
   no es "LLM o modelo de mundo", sino **qué objetivo de aprendizaje produce mejores
   abstracciones, y con qué eficiencia**.
3. **El razonamiento en cadena sigue siendo tokens.** Que un modelo "piense" más tiempo
   no implica que use símbolos ni un modelo latente del mundo. Es una concesión
   funcional, no necesariamente arquitectónica.

**Formulación falsable que proponemos:**
> Con el mismo presupuesto, un objetivo predictivo **en el espacio latente** (JEPA)
> produce representaciones más abstractas que uno predictivo **en el espacio de
> observaciones**, sobre todo cuando las observaciones contienen detalles impredecibles e
> irrelevantes. Esas representaciones permiten además extraer **leyes simbólicas** del
> sistema.

Si se cumple, apoya la parte JEPA de la tesis y muestra un puente concreto hacia lo
simbólico. Si no se cumple (si el objetivo generativo iguala a JEPA incluso con mucho
ruido), la ventaja de predecir en el espacio latente no es general.

## Experimento E6: JEPA frente a predicción generativa en un mundo de osciladores

**Mundo.** Dos osciladores de fase acoplados (modelo de Kuramoto): dθᵢ/dt = ωᵢ +
K·sin(θⱼ − θᵢ). Cada secuencia tiene sus propias ω₁, ω₂ y K. No se observan las fases:
se observan **32 "canales" de sensor** que mezclan de forma no lineal los osciladores,
más canales distractores de **ruido impredecible** con desviación σ_d. Es una analogía
deliberada con el EEG, donde los electrodos registran mezclas de fuentes más ruido. Y
los osciladores acoplados son uno de los intereses que Luna generó por su cuenta.

**Modelos** (mismo codificador y mismo presupuesto):
- `jepa`: predice el latente futuro z(t+k) a partir de z(t); objetivo con codificador EMA
  y regularización de varianza y covarianza para evitar el colapso.
- `generativo`: predice la observación futura x(t+k) en el espacio de sensores.
- `autoencoder`: reconstruye x(t) (sin predicción).
- `aleatorio`: codificador sin entrenar (línea base).

**Medidas:**
1. **Abstracción:** sonda lineal congelada de z(t) a las variables ocultas (seno y
   coseno de cada fase y de la diferencia de fase). Se reporta R² en secuencias nuevas.
2. **Fuera de distribución:** el mismo R² con acoplamientos K mayores que los vistos.
3. **Puente simbólico:** a partir de la diferencia de fase decodificada, una regresión
   dispersa sobre una biblioteca de funciones candidatas (estilo SINDy) recupera la ley
   dΔθ/dt = Δω − 2K·sin(Δθ). Se mide la correlación entre la K recuperada y la real.

**Hipótesis (registradas antes de correrlo):**
- **H1.** Sin distractores, `jepa` ≈ `generativo` > `autoencoder` > `aleatorio` en R².
- **H2.** Al aumentar σ_d, `generativo` y `autoencoder` pierden más R² que `jepa`.
- **H3.** La ley simbólica se recupera mejor a partir de las representaciones de
  `jepa` (correlación de K más alta).
- **Refutación:** si `generativo` ≥ `jepa` con σ_d alta, H2 cae.

### Piloto (CPU, 1 semilla, 800 pasos) y registro de E6b

Resultado del piloto con σ = 3 y ruido blanco: `generativo` R² 0.80 > `jepa` 0.63 >
`autoencoder` 0.50. **No apoya H2.** Explicación probable: el ruido blanco es
*impredecible*, así que el objetivo generativo aprende a predecir su media (0) y no
gasta capacidad en él. El autoencoder sí, porque reconstruye el presente. El argumento
de LeCun es más fuerte con detalles **predecibles pero irrelevantes**, que un modelo
generativo *debe* modelar para predecir bien y que JEPA *puede* ignorar. Por eso el ruido
blanco es una prueba débil del argumento.

**E6b (registrado antes de correrlo):** mismos modelos, pero los canales distractores
contienen la dinámica de dos osciladores rápidos e independientes (predecible e
irrelevante), `--tipo estructurado`.
- **H2b.** Con σ alta, `jepa` ≥ `generativo` en R² y en la recuperación de K.
- **Riesgo conocido:** la regularización de varianza de JEPA obliga a usar todas las
  dimensiones y podría empujarlo a codificar también el distractor. Si H2b falla, esa
  será la primera explicación a examinar (con una ablación del peso de la
  regularización), no un motivo para cambiar la hipótesis.

**Limitaciones:** es un mundo de juguete y de baja dimensión. Un resultado positivo
justifica escalar (señales reales: ECG, EEG o variabilidad cardiaca), no generalizar
directamente.

## Cómo encaja en Luna

| Pieza | Tipo de modelo de mundo |
|---|---|
| Grafo de creencias (fase 2) | Simbólico: lo que cree sobre el mundo y sobre Usx |
| Biblioteca de programas (E1, C4) | Simbólico procedimental: reglas ejecutables |
| JEPA (E6) | Latente y aprendido: dinámica de un dominio |
| Extracción de leyes (E6) | Puente latente → simbólico |

Esta es la versión concreta de la "abstracción mediante símbolos" que Usx planteó al
principio: aprender un espacio latente predictivo y, de él, **destilar símbolos**
(leyes, variables) que entren en el grafo de creencias y en el laboratorio mental.

## Relación con E2 (mirar dentro del modelo de lenguaje)

E2 aplica a Qwen la pregunta de Othello-GPT: ¿hay en sus activaciones una
representación lineal del estado de un mundo? Por ejemplo, el estado de las listas en
las tareas de E1. Si la hay, la "capitulación" sería menos necesaria de lo que dice la
tesis: el modelo de mundo estaría, pero sin usarse bien. Si no la hay, la tesis gana
fuerza.
