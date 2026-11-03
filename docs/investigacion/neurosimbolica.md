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
