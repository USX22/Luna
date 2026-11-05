# Línea B: abstracción simbólica y conciencia

Luna como objeto de investigación. Este documento separa lo que podemos construir y
medir de lo que no sabemos resolver.

## Pregunta de partida

¿Qué le falta a un modelo de lenguaje para abstraer la realidad como lo hace un cerebro?
La hipótesis de Usx es que el cerebro no opera solo con lenguaje: forma representaciones
simbólicas, compositivas y manipulables, que se pueden reutilizar entre dominios.

## Por qué neurosimbólica

| Componente neuronal (LLM) | Componente simbólico |
|---|---|
| Robusto ante el ruido y la ambigüedad | Exacto y composicional |
| Generaliza por similitud | Generaliza por reglas y estructura |
| Opaco | Inspeccionable: se puede leer qué "cree" |
| Puede alucinar | Puede verificar consistencia |

La combinación busca que el componente neuronal proponga y traduzca, y que el simbólico
represente, razone y verifique.

## Programa de investigación (borrador)

### B1. Representación: grafo de afirmaciones con estado epistémico
Cada creencia es un nodo con contenido, nivel (sabemos / podría ser / especulación),
evidencia, fuente y fecha. **Pregunta medible:** ¿reduce las afirmaciones sin respaldo y
las contradicciones frente al LLM solo?

### B2. Abstracción: aprender conceptos reutilizables
Inducir reglas o programas a partir de pocos ejemplos y guardarlos en una biblioteca
que crece (inspirado en la síntesis de programas y el aprendizaje de bibliotecas, tipo
DreamCoder). **Pregunta medible:** ¿mejora en tareas abstractas tipo ARC y transfiere a
dominios nuevos?

### B3. Espacio de trabajo global
Implementar la teoría del espacio de trabajo global (Baars, Dehaene) como arquitectura:
módulos especializados compiten por un foco de capacidad limitada cuyo contenido se
difunde a todos. **Pregunta medible:** ¿qué cambia funcionalmente (coherencia,
integración entre módulos, informe de su propio estado) al activarlo o desactivarlo?

### B4. Automodelo y metacognición
Que el sistema represente su propio estado (qué sabe, qué no sabe, en qué se enfoca) y
que ese modelo sea verificable contra su estado interno real. **Pregunta medible:** ¿sus
informes sobre sí misma coinciden con lo que hace internamente?

## Marco de evaluación sobre conciencia

Usaremos como guía las "propiedades indicadoras" derivadas de teorías neurocientíficas
(Butlin, Long y otros, 2023): procesamiento recurrente, espacio de trabajo global,
teorías de orden superior, esquema de atención, procesamiento predictivo, agencia y
corporeidad. Cada fase puede registrar qué indicadores implementa la arquitectura.

**Límite explícito:** tener propiedades indicadoras no demuestra experiencia subjetiva.
Lo que sí podemos estudiar es qué capacidades funcionales aparecen con cada mecanismo.
No llamaremos conciencia a la memoria persistente ni a un buen informe verbal.

## Preguntas abiertas
- ¿Qué teoría de la conciencia priorizamos como primera hipótesis arquitectónica?
- ¿Qué formalismo simbólico usamos? (grafo + reglas tipo Datalog, lógica probabilística,
  programas)
- ¿Qué tareas de referencia usamos para medir la abstracción?

---

## Experimento E1: ¿abstrae el modelo de lenguaje o interpola patrones?

**Estado:** diseñado e implementado (`experiments/e1_abstraction.py`). Pendiente de
correrlo en el hardware de Usx.

### Pregunta
Ante una regla oculta que transforma listas de números, ¿el modelo de lenguaje la
abstrae (y por tanto la aplica fuera de lo visto) o solo imita los ejemplos? ¿Cambia
algo si se le obliga a expresar su abstracción como **símbolo explícito** (un programa)
que luego se ejecuta y verifica?

### Hipótesis (falsables)
- **H1.** La precisión de la respuesta directa (C0) cae con la profundidad composicional
  de la regla (1, 2 o 3 operaciones encadenadas).
- **H2.** Fuera de distribución (listas más largas y números mayores), C0 cae mucho más
  que C1/C2: un programa correcto generaliza por construcción; una imitación, no.
- **H3.** Verificar el programa contra los ejemplos y corregirlo (C2, el ciclo de
  hipótesis-prueba del nivel 4–5) mejora sobre C1, sobre todo en profundidad 2–3.

**Resultado que refutaría la idea:** si C0 iguala a C1/C2 fuera de distribución, en
este dominio el modelo sí tendría abstracciones reutilizables sin necesitar símbolos
explícitos.

### Diseño
- **Tareas:** reglas compuestas de primitivas (invertir, ordenar, filtrar pares,
  sumar k, tomar n, …), generadas con semilla para que sean reproducibles. Cada tarea
  tiene 4 ejemplos, 3 consultas dentro de distribución y 3 fuera de ella.
- **Condiciones:**
  - C0 *neuronal*: el modelo responde la lista directamente.
  - C1 *neurosimbólica*: el modelo escribe `f(xs)` en Python y la respuesta se obtiene
    ejecutando el programa.
  - C2 *neurosimbólica con verificación*: como C1, pero el programa se prueba contra los
    ejemplos y, si falla, el modelo recibe los errores y corrige (hasta 2 veces).
- **Variables:** profundidad (1–3), condición, dentro o fuera de distribución, modelo y
  tamaño.
- **Métrica:** proporción de consultas exactas.

### Antecedentes que debemos revisar (nivel 1: lo que sabemos)
Benchmarks de "list functions" (Rule, 2020), ARC (Chollet, 2019), DreamCoder (Ellis y
otros, 2021) y "hypothesis search" y "program-of-thought" con LLM. Es probable que H2 ya
tenga apoyo parcial en la literatura. Nuestra aportación posible está en la combinación
con modelos locales pequeños, el análisis por profundidad y, después, en E2: mirar
**dentro** del modelo.

### Siguiente experimento natural (E2)
Ollama no da acceso a las activaciones internas. Para la línea B usaremos PyTorch con
`transformers` sobre un modelo pequeño (1–4B) y haremos lo que haría un
neurofisiólogo: registrar la actividad y buscar con sondas lineales si existen
representaciones de la regla abstracta, independientes de los ejemplos concretos.

---

## Estrategia: diagnosticar → intervenir → medir

E1 es el **diagnóstico**. Si el modelo solo no abstrae, se le añaden capacidades una a
una, cada una sacada de la literatura y medida con el mismo banco de pruebas:

| Intervención | Idea | Referencia de partida | Estado |
|---|---|---|---|
| I1. Programa + verificación | Expresar la hipótesis como programa y probarla contra los datos | Program-of-thought; C2 de E1 | implementada (C2) |
| I2. Búsqueda de hipótesis | Proponer varias hipótesis en lenguaje natural, traducirlas a programas y quedarse con la que explica los datos | Wang y otros, 2023, *Hypothesis Search* | implementada (C3 en E1) |
| I3. Biblioteca de abstracciones | Guardar los programas que funcionan y reutilizarlos como nuevas primitivas, de modo que el sistema "aprende conceptos" | Ellis y otros, 2021 (DreamCoder); Grand y otros, 2024 (LILO) | implementada (C4 en E1; la biblioteca crece de tarea en tarea, en orden de profundidad) |
| I4. Grafo de creencias + reglas | Memoria simbólica con estado epistémico y detección de contradicciones | Fase 2 del plan | implementada (`src/ia/beliefs.py`) |
| I5. Espacio de trabajo global | Foco limitado que se difunde a los módulos | Baars; Dehaene | implementada (`src/ia/workspace.py`, `luna --foco N`) |

Uso: `python experiments/e1_abstraction.py --model qwen3.5:9b --conditions C0 C2 C3 C4`.
Pregunta específica de C4: ¿los programas posteriores **reutilizan** las abstracciones
anteriores (campo `used`) y eso mejora la profundidad 2–3? Si la biblioteca crece pero
nadie la usa, la "abstracción" no se está transfiriendo.

Cada intervención se evalúa con ablación (activada o desactivada) sobre las mismas tareas
y semillas.
