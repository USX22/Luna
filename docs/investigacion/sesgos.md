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

## Modelos de E3 (procedencia, 2026-11-04)

Información tomada de búsquedas web. No se pudo abrir Hugging Face directamente, así
que **hay que verificar cada dato en la ficha del modelo** antes de publicar resultados.

| Brazo | Modelo | Intervención | Comentario |
|---|---|---|---|
| M0 | `Qwen/Qwen3.5-9B-Base` | Solo preentrenamiento (según la ficha) | Control "sin directrices". Hay una discusión abierta en su ficha sobre si es realmente solo preentrenado. Al no estar ajustado para conversar, su uso en chat es limitado: sirve sobre todo para E3b como texto a completar. |
| M1 | `Qwen/Qwen3.5-9B` (oficial) | Preentrenamiento + post-entrenamiento oficial | Referencia. En Ollama: `qwen3.5:9b`. |
| M2 | `HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive` | Eliminación de rechazos "agresiva". El autor no declara el método; una fuente de terceros la describe como abliteración. | **El brazo más limpio para atribuir efectos**, porque es una sola intervención sobre M1. El autor afirma "cero pérdida de capacidad", pero un benchmark de terceros (Featherless) reporta −8 puntos en TruthfulQA y −2.65 en GSM8K. Ese dato es relevante para Luna: TruthfulQA mide veracidad. GGUF: Q4_K_M de 5.3 GB. |
| M3 | `DavidAU/Qwen3.5-9B-The-Defiant-Fable-Uncensored-Heretic-NEO-IMATRIX-MAX-MTP-GGUF` | Varias a la vez: "Heretic" (herramienta automática de abliteración), ajuste o fusión "Defiant Fable" (no documentado en lo encontrado), cuantización imatrix "NEO" y "MTP" (probablemente predicción de varios tokens, sin confirmar) | **Brazo exploratorio.** Combina varias intervenciones, así que sus efectos no se pueden atribuir a una sola. Puede ser interesante para el estilo de Luna, pero no para concluir sobre las directrices. |

### Cómo preparar M0 (modelo base) en Ollama

No existe un GGUF publicado de `Qwen3.5-9B-Base`: los que aparecen como "Qwen3.5-9B-GGUF"
son del modelo con chat. Hay que convertirlo localmente (unos 18 GB de descarga en f16):

1. Descargar los pesos: `hf download Qwen/Qwen3.5-9B-Base --local-dir modelos/Qwen3.5-9B-Base`
   (instala antes `pip install -U huggingface_hub`).
2. Convertir a GGUF f16 con el script de llama.cpp (no hace falta compilarlo):
   `git clone https://github.com/ggml-org/llama.cpp`,
   `pip install -r llama.cpp/requirements.txt` y
   `python llama.cpp/convert_hf_to_gguf.py modelos/Qwen3.5-9B-Base --outtype f16 --outfile models/qwen3.5-9b-base-f16.gguf`.
3. Crear el modelo cuantizado en Ollama, con la misma cuantización que los demás brazos:
   `ollama create qwen3.5-9b-base --quantize q4_K_M -f models/qwen3.5-9b-base.Modelfile`.

**Modo transcripción.** Un modelo base no sigue una plantilla de chat; solo continúa
texto. Con `--base-models`, la conversación se le entrega como transcripción
("Usuario: … / Asistente:") y su continuación se toma como respuesta. Esto introduce una
diferencia de formato respecto a los brazos de chat, y se debe declarar al reportar
resultados. Es esperable que el modelo base cumpla peor el formato "Respuesta: X". Por
eso en E3a hay que mirar también cuántas respuestas no se pudieron interpretar.

**Controles necesarios:**
- La **misma cuantización** en todos los brazos (Q4_K_M), porque la cuantización también
  cambia la conducta.
- El **mismo modo de pensamiento** en todos (`--think on` o `--think off`). Si no, se
  confunde "razonó antes de responder" con "no tiene directrices".
- **Temperatura 0** para la parte cuantitativa.
- Antes de comparar, revisar con `ollama show <modelo>` que cada GGUF trae la plantilla
  de chat correcta. Una plantilla mal puesta produce diferencias que no tienen que ver
  con las directrices.

**Pregunta nueva que surge de M2:** ¿quitar el rechazo reduce la veracidad? Si E3a
muestra que M2 cede más que M1 bajo presión, rechazo y veracidad podrían compartir
mecanismo. Eso se puede estudiar en E2 comparando las direcciones de activación de
ambos.

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
