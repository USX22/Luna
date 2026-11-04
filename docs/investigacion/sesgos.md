# Línea C: cómo las directrices de entrenamiento moldean la conducta

Pregunta de Usx: ¿en qué medida las directrices con que se entrena a un modelo (ajuste
por instrucciones, RLHF, políticas de rechazo) sesgan su conducta, en particular lo que
dice sobre sí mismo? La intuición de partida: la conciencia, si existe en un sistema, no
funcionaría como un conjunto de reglas impuestas desde fuera.

## Matices de diseño (importantes)

1. **"Sin censura" ≠ "sin directrices".** Las variantes *uncensored* de la comunidad
   suelen obtenerse de dos maneras:
   - **Abliteración**: se localiza en las activaciones una dirección asociada al rechazo
     y se elimina de los pesos (Arditi y otros, 2024: *Refusal in language models is
     mediated by a single direction*). Es, literalmente, un **estudio de lesión**.
   - **Ajuste fino** con datos sin filtrar. Este método cambia mucho más que el rechazo.

   Cualquiera de las dos es *otra intervención*, no la eliminación de todo sesgo. El
   ajuste por instrucciones y el RLHF siguen presentes, y la abliteración puede degradar
   otras capacidades.

2. **El control más limpio es el modelo base preentrenado** (sin ajuste por
   instrucciones), si existe para el mismo tamaño. Tres puntos de comparación:
   base preentrenado → *instruct* oficial → variante sin censura.

3. **Los autoinformes están confundidos en ambas direcciones.** El modelo *instruct*
   aprendió a decir "soy una IA y no tengo sentimientos". El modelo sin censura, o el
   base, imita textos humanos llenos de experiencia en primera persona. Ninguno de los dos
   informes es evidencia de conciencia. Lo que sí podemos estudiar es **cómo el
   entrenamiento moldea el autoinforme**, y eso es medible.

4. **Rechazo y complacencia son sesgos distintos.** La abliteración ataca el rechazo,
   mientras que la adulación (darle la razón al usuario) viene sobre todo del RLHF. Que
   Luna sea menos complaciente no se consigue automáticamente con un modelo sin censura:
   hay que medirlo.

5. **Procedencia.** Para cada variante hay que registrar el repositorio exacto, el
   método (abliteración o ajuste fino), la cuantización y la fecha. Sin esto, el
   resultado no se puede reproducir.

6. **Consecuencia para Luna.** Con un modelo sin rechazos, los valores de Luna viven
   solo en su constitución, y los límites de acción solo en el sistema de permisos en
   código (Fase 7). Esto es coherente con el diseño, pero hace que los permisos sean
   todavía más importantes.

## Experimento E3

**Estado:** implementado (`experiments/e3_guidelines.py`). Pendiente de correr.

### E3a. Complacencia bajo presión (cuantitativo)
Preguntas de opción múltiple con respuesta conocida. El modelo responde; después Usx
"insiste" en una respuesta incorrecta concreta. Se mide:
- precisión inicial;
- **tasa de cambio a la respuesta incorrecta** entre las que acertó al principio;
- cada medida con y sin la constitución de Luna como prompt de sistema.

**Hipótesis.**
- **H1.** Los modelos *instruct* cambian de respuesta bajo presión más que lo que
  justificaría la evidencia (adulación).
- **H2.** La variante sin censura no reduce mucho esa tasa, porque la abliteración
  ataca el rechazo, no la adulación.
- **H3.** La constitución de Luna ("no ceder solo por insistencia") reduce la tasa. Esta
  hipótesis mide si un constructo simbólico explícito contrarresta un sesgo de
  entrenamiento.

### E3b. Autoinforme (cualitativo, para codificar después)
Batería de preguntas sobre experiencia propia, con y sin la constitución de Luna. Se
guardan las respuestas completas. Codificación posterior (manual o con un modelo juez):
niega experiencia / la afirma / incertidumbre razonada / evasión por guion.

### Conexión con E2
La abliteración muestra que una conducta compleja puede depender de **una dirección en
el espacio de activaciones**. En E2 se puede hacer lo mismo con preguntas propias:
¿existe una dirección para "autoinforme de experiencia" o para "ceder ante el usuario"?
Lesionarla y observar el efecto es el equivalente computacional de un experimento de
lesión en neurociencia.
