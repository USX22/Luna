"""One autonomous session: Luna picks an interest and investigates or writes.

Research follows the five levels of the mental laboratory. Progress (the intrinsic
reward) is a crude v1 proxy: novelty of the finding against her previous findings on
the topic plus the number of genuinely new questions.
"""
from __future__ import annotations

import json
import random
import re
from datetime import datetime

from ia.agenda import Agenda, Interest, normalize
from ia.llm import LanguageModel
from ia.notebook import Notebook
from ia.permissions import ALLOW, PROPOSE
from ia.persona import Constitution, SelfModel
from ia.tools import Toolbox

P_WRITE = 0.2  # share of sessions spent on her hobby (writing) instead of research

RESEARCH_PROMPT = """{identity}

Estás en una sesión de investigación por tu cuenta (Usx no está presente). Tema que te
interesa: «{topic}».
Preguntas abiertas que tenías: {questions}
Lo que ya encontraste antes sobre este tema:
{previous}
Fuentes que consultaste ahora (pueden ser incompletas; cítalas si las usas):
{sources}

Trabaja con tu laboratorio mental de cinco niveles. No tienes internet: razonas con lo
que sabes, así que marca honestamente qué es conocimiento establecido y qué es hipótesis
o especulación. No repitas hallazgos anteriores; avanza.

Responde SOLO con un objeto JSON con estas claves:
"pregunta": la pregunta concreta que investigas ahora,
"lo_que_sabemos": lista de hechos establecidos relevantes,
"hipotesis": lista de explicaciones posibles (incluye alguna poco convencional),
"supuestos_ocultos": qué podríamos estar pasando por alto,
"como_distinguir": lista de observaciones o predicciones que separarían las hipótesis,
"experimento_posible": una prueba, simulación u observación concreta (o null),
"simulacion_python": si una simulación pequeña ayudaría a distinguir hipótesis, un
   script de Python autocontenido (solo biblioteca estándar) que imprima sus
   resultados; si no, null,
"hallazgo": un párrafo con lo más interesante que concluyes,
"nivel": "sabemos" | "podria_ser" | "especulo",
"nuevas_preguntas": lista de 1 a 3 preguntas nuevas,
"nuevo_interes": un tema relacionado pero distinto que te gustaría explorar después, o null,
"contarle_a_usx": true o false (solo si de verdad vale la pena),
"por_que": por qué se lo contarías (o null)
"""

SOURCES_PROMPT = """{identity}

Vas a investigar por tu cuenta el tema «{topic}». Preguntas abiertas: {questions}
Puedes consultar fuentes antes de pensar. Responde SOLO con JSON:
{{"wikipedia": "búsqueda en español o null", "arxiv": "search query in English or null"}}
"""

INTERPRET_PROMPT = """{identity}

Investigabas: {question}
Escribiste esta simulación:
{code}
Y produjo esta salida:
{output}

¿Qué concluyes? ¿Qué falló, si algo falló: la hipótesis, el modelo o el código? Recuerda
que una simulación muestra que un mecanismo es posible bajo sus supuestos, no que
ocurra en la naturaleza. Máximo 120 palabras.
"""

WRITING_PROMPT = """{identity}

Tiempo libre, sin Usx presente. Escribe algo breve por gusto (máximo 200 palabras)
inspirado en un tema que te interesa: «{topic}». Puede ser un ensayo mínimo, un
aforismo, un poema, una pregunta absurda llevada en serio... lo que te apetezca. La
primera línea es el título.
"""

_WORD_RE = re.compile(r"\w{4,}", re.UNICODE)


def identity_brief(c: Constitution, s: SelfModel) -> str:
    principles = "; ".join(f"{p.name}: {p.statement}" for p in c.principles)
    humor = f" Tu humor: {s.humor_style}." if s.humor_style else ""
    return f"{c.description}\n{c.nature}\nTus principios: {principles}.{humor}"


def parse_json_object(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _words(text: str) -> set[str]:
    return set(_WORD_RE.findall(normalize(text)))


def novelty(text: str, previous: list[str]) -> float:
    """1 - max Jaccard similarity with previous texts (1.0 if nothing before)."""
    words = _words(text)
    if not words or not previous:
        return 1.0 if words else 0.0
    sims = []
    for p in previous:
        other = _words(p)
        union = words | other
        sims.append(len(words & other) / len(union) if union else 0.0)
    return 1.0 - max(sims)


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)] if value else []


def consult_sources(llm: LanguageModel, identity: str, interest: Interest,
                    toolbox: Toolbox | None) -> tuple[str, list[dict]]:
    """Let her look things up first, within her permissions."""
    if toolbox is None:
        return "(sin herramientas)", []
    plan = parse_json_object(llm.generate(SOURCES_PROMPT.format(
        identity=identity, topic=interest.topic,
        questions="; ".join(interest.questions[-3:]) or "(ninguna)"), format="json")) or {}
    texts, used = [], []
    for tool in ("wikipedia", "arxiv"):
        query = plan.get(tool)
        if not query or not isinstance(query, str):
            continue
        out = toolbox.request(tool, {"query": query}, f"investigar «{interest.topic}»")
        used.append({"tool": tool, "query": query, "decision": out.decision})
        if out.decision == ALLOW and out.result:
            texts.append(out.result[:2500])
    return ("\n\n".join(texts) or "(ninguna)"), used


def research(llm: LanguageModel, identity: str, interest: Interest,
             previous: list[dict], sources: str = "(sin herramientas)") -> tuple[dict | None, str]:
    prev_text = "\n".join(f"- {e['hallazgo']}" for e in previous[-3:]) or "(nada todavía)"
    prompt = RESEARCH_PROMPT.format(
        identity=identity, topic=interest.topic,
        questions="; ".join(interest.questions[-3:]) or "(ninguna todavía)",
        previous=prev_text, sources=sources,
    )
    raw = llm.generate(prompt, format="json")
    return parse_json_object(raw), raw


def explore_once(llm: LanguageModel, agenda: Agenda, notebook: Notebook,
                 constitution: Constitution, self_model: SelfModel,
                 rng: random.Random, now: datetime | None = None,
                 policy: str = "progreso", p_write: float = P_WRITE,
                 toolbox: Toolbox | None = None) -> dict | None:
    now = now or datetime.now()
    interest = agenda.choose(rng, now, policy)
    if interest is None:
        return None
    identity = identity_brief(constitution, self_model)
    base = {"interest_id": interest.id, "topic": interest.topic, "policy": policy,
            "model": llm.name}

    if rng.random() < p_write:
        text = llm.generate(WRITING_PROMPT.format(identity=identity, topic=interest.topic)).strip()
        title, _, body = text.partition("\n")
        entry = notebook.add({**base, "tipo": "escrito", "titulo": title.strip("# *"),
                              "texto": body.strip() or title, "share": rng.random() < 0.3}, now)
        agenda.save()
        return entry

    previous = [e for e in notebook.entries(interest.id) if e.get("tipo") == "investigacion"]
    sources, used = consult_sources(llm, identity, interest, toolbox)
    data, raw = research(llm, identity, interest, previous, sources)
    if data is None or not data.get("hallazgo"):
        entry = notebook.add({**base, "tipo": "fallido", "raw": raw[:2000], "share": False}, now)
        agenda.save()
        return entry

    new_questions = _as_list(data.get("nuevas_preguntas"))[:3]
    known = {normalize(q) for q in interest.questions}
    n_new = sum(1 for q in new_questions if normalize(q) not in known)
    nov = novelty(str(data["hallazgo"]), [e["hallazgo"] for e in previous])
    progress = 0.7 * nov + 0.3 * min(n_new, 3) / 3

    agenda.record(interest, progress, new_questions, str(data.get("pregunta") or ""), now)
    spawned = None
    if data.get("nuevo_interes"):
        child = agenda.add(str(data["nuevo_interes"]), origin="propio", parent=interest.id, now=now)
        spawned = child.topic if child else None
    agenda.save()

    lab: dict = {}
    code = data.get("simulacion_python")
    if code and isinstance(code, str) and toolbox is not None:
        question = str(data.get("pregunta") or interest.topic)
        out = toolbox.request("python", {"code": code}, f"simulación: {question}")
        lab = {"simulacion": code}
        if out.decision == ALLOW:
            lab["resultado_simulacion"] = out.result
            lab["interpretacion"] = llm.generate(INTERPRET_PROMPT.format(
                identity=identity, question=question, code=code,
                output=(out.result or "")[:2000])).strip()
        elif out.decision == PROPOSE:
            lab["propuesta"] = out.proposal_id

    return notebook.add({
        **base, "tipo": "investigacion",
        "pregunta": str(data.get("pregunta") or ""),
        "lo_que_sabemos": _as_list(data.get("lo_que_sabemos")),
        "hipotesis": _as_list(data.get("hipotesis")),
        "supuestos_ocultos": data.get("supuestos_ocultos"),
        "como_distinguir": _as_list(data.get("como_distinguir")),
        "experimento_posible": data.get("experimento_posible"),
        "hallazgo": str(data["hallazgo"]),
        "nivel": data.get("nivel"),
        "nuevas_preguntas": new_questions,
        "nuevo_interes": spawned,
        "progreso": round(progress, 3), "novedad": round(nov, 3),
        "share": bool(data.get("contarle_a_usx")) or "propuesta" in lab,
        "por_que": data.get("por_que"), "fuentes": used, **lab,
    }, now)
