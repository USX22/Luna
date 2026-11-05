"""Luna's tools and the toolbox that runs them under the permission policy."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable

from ia.permissions import (
    ALLOW, CONFIRM_WORD, DENY, PROPOSE, JsonlStore, Policy, Proposals, now_iso,
)
from ia.safety import find_personal_data, injection_signals

USER_AGENT = "Luna-research-assistant/0.1 (personal research project)"
Fetch = Callable[[str], bytes]


def http_get(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def wikipedia(args: dict, fetch: Fetch = http_get) -> str:
    """Search Wikipedia and return the intro of the top results."""
    lang = args.get("lang", "es")
    base = f"https://{lang}.wikipedia.org/w/api.php?"
    q = urllib.parse.urlencode({"action": "query", "list": "search", "format": "json",
                                "srsearch": args["query"], "srlimit": 2})
    hits = json.loads(fetch(base + q))["query"]["search"]
    if not hits:
        return "Sin resultados en Wikipedia."
    out = []
    for hit in hits:
        q = urllib.parse.urlencode({"action": "query", "prop": "extracts", "exintro": 1,
                                    "explaintext": 1, "format": "json", "titles": hit["title"]})
        pages = json.loads(fetch(base + q))["query"]["pages"]
        extract = next(iter(pages.values())).get("extract", "")
        out.append(f"## {hit['title']} (Wikipedia {lang})\n{extract[:1500]}")
    return "\n\n".join(out)


_ATOM = "{http://www.w3.org/2005/Atom}"


def arxiv(args: dict, fetch: Fetch = http_get) -> str:
    """Search arXiv and return title, date, id and abstract of the top results."""
    q = urllib.parse.urlencode({"search_query": f"all:{args['query']}", "max_results": 3,
                                "sortBy": "relevance"})
    root = ET.fromstring(fetch("https://export.arxiv.org/api/query?" + q))
    out = []
    for entry in root.findall(f"{_ATOM}entry"):
        title = " ".join(entry.findtext(f"{_ATOM}title", "").split())
        summary = " ".join(entry.findtext(f"{_ATOM}summary", "").split())
        out.append(f"## {title} ({entry.findtext(f'{_ATOM}published', '')[:10]}, "
                   f"{entry.findtext(f'{_ATOM}id', '')})\n{summary[:1200]}")
    return "\n\n".join(out) or "Sin resultados en arXiv."


def python_run(args: dict, timeout: float = 30.0) -> str:
    """Run a Python script in a separate process, in an empty temp dir, with a timeout.

    Isolates crashes and infinite loops. NOT a security sandbox.
    """
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run([sys.executable, "-I", "-c", args["code"]], cwd=tmp,
                                  capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"[tiempo agotado tras {timeout:.0f} s]"
    out = proc.stdout[-4000:]
    if proc.returncode != 0:
        out += f"\n[error, código {proc.returncode}]\n{proc.stderr[-2000:]}"
    return out or "[sin salida]"


@dataclass(frozen=True)
class Tool:
    name: str
    level: int
    description: str
    run: Callable[[dict], str]


def default_tools(fetch: Fetch = http_get) -> dict[str, Tool]:
    return {
        "wikipedia": Tool("wikipedia", 1, "buscar en Wikipedia (solo lectura)",
                          lambda a: wikipedia(a, fetch)),
        "arxiv": Tool("arxiv", 1, "buscar artículos en arXiv (solo lectura)",
                      lambda a: arxiv(a, fetch)),
        "python": Tool("python", 2, "ejecutar una simulación en Python", python_run),
    }


@dataclass
class Outcome:
    decision: str
    result: str | None = None
    proposal_id: str | None = None
    note: str = ""            # why it was denied, if it was
    injection: list[str] = None  # suspicious instructions found in the result


class Toolbox:
    def __init__(self, policy: Policy, tools: dict[str, Tool], log: JsonlStore,
                 proposals: Proposals):
        self.policy, self.tools, self.log, self.proposals = policy, tools, log, proposals

    def _run(self, tool: Tool, args: dict) -> str:
        try:
            return tool.run(args)
        except Exception as exc:  # network errors, bad args...
            return f"[fallo de la herramienta: {exc}]"

    def request(self, name: str, args: dict, reason: str) -> Outcome:
        tool = self.tools.get(name)
        if tool is None:
            self.log.append({"ts": now_iso(), "tool": name, "decision": DENY, "reason": reason})
            return Outcome(DENY)
        decision = self.policy.decide(name, tool.level)
        entry = {"ts": now_iso(), "tool": name, "args": args, "reason": reason,
                 "decision": decision}
        if decision == DENY:
            note = "parada de emergencia activa" if self.policy.stopped else "no permitido"
            self.log.append({**entry, "note": note})
            return Outcome(DENY, note=note)
        leaked = find_personal_data(str(args.get("query", "")), self.policy.private_terms)
        if leaked and name != "python":
            self.log.append({**entry, "decision": DENY, "note": "datos personales en la consulta"})
            return Outcome(DENY, note="datos personales en la consulta")
        if decision == ALLOW:
            result = self._run(tool, args)
            signals = injection_signals(result)
            self.log.append({**entry, "result": result[:2000],
                             **({"inyeccion": signals} if signals else {})})
            return Outcome(ALLOW, result, injection=signals)
        proposal = self.proposals.add(name, args, reason, self.policy.level(name, tool.level))
        self.log.append({**entry, "proposal": proposal["id"]})
        return Outcome(PROPOSE, proposal_id=proposal["id"])

    def approve(self, pid: str, confirmation: str = "") -> str:
        p = self.proposals.get(pid)
        if p is None or p["status"] != "pendiente":
            return "No hay una propuesta pendiente con ese id."
        if self.policy.stopped:
            return "La parada de emergencia está activa (luna-alto --reanudar para quitarla)."
        if p["level"] >= 3 and confirmation != CONFIRM_WORD:
            return f"Es una acción de nivel 3: escribe /aprobar {pid} {CONFIRM_WORD}"
        tool = self.tools.get(p["tool"])
        if tool is None:
            return "Esa herramienta ya no existe."
        result = self._run(tool, p["args"])
        self.proposals.update(pid, status="ejecutada", result=result[:4000])
        self.log.append({"ts": now_iso(), "tool": p["tool"], "args": p["args"],
                         "decision": "aprobada por Usx", "proposal": pid,
                         "result": result[:2000]})
        return result

    def cancel_all(self, reason: str) -> int:
        pending = self.proposals.pending()
        for p in pending:
            self.proposals.update(p["id"], status="cancelada", result=reason)
            self.log.append({"ts": now_iso(), "tool": p["tool"], "decision": "cancelada",
                             "proposal": p["id"], "reason": reason})
        return len(pending)

    def reject(self, pid: str) -> bool:
        p = self.proposals.get(pid)
        if p is None or p["status"] != "pendiente":
            return False
        self.proposals.update(pid, status="rechazada")
        self.log.append({"ts": now_iso(), "tool": p["tool"], "decision": "rechazada por Usx",
                         "proposal": pid})
        return True
