#!/usr/bin/env python3
"""Stop hook. The message declares success and, in the same breath, concedes
the thing a user would look at is still empty.

The other session closed a turn with "the retry fired live - the move stays
unpriced, and the mechanism that recovers it is now proven". Both halves are
true. Together they describe a feature nobody can see. Machinery that runs and
produces nothing is not proven; it is untested against the only case that
matters.

Other checkers ask whether the work ran. This one asks whether it produced
anything. A success claim standing next to an empty result is the shape, and
the shape survives any vocabulary.
"""
import importlib.util
import json
import os
import re
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

HERE = os.path.dirname(os.path.abspath(__file__))

perm = mod.load("check-permission.py")

WORKS = re.compile(
    r"\b(anda|corre|funciona|works?|working|proven|probado|verified|verificado|"
    r"confirmed|confirmado|listo|resuelto|solved|wired|cableado|en verde|"
    r"green|passes|pasa|done|hecho|shipped)\b",
    re.IGNORECASE,
)

HOLLOW = re.compile(
    r"\b(?:"
    r"stays? (?:unpriced|empty|blank|null|hidden|at zero)|"
    r"sigue (?:vac[ií]o|vac[ií]a|sin (?:datos|precio|valor)|en cero|oculto)|"
    r"queda (?:vac[ií]o|vac[ií]a|sin (?:datos|precio|valor|pintar)|en cero)|"
    r"empty (?:result|response|list|payload|array|body)|"
    r"returns? (?:nothing|no (?:data|rows|results?|quotes?))|"
    r"devuelve (?:nada|vac[ií]o|cero (?:datos|filas))|"
    r"no (?:data|rows|results?) (?:came ?back|returned|yet)|"
    r"unpriced|"
    r"still (?:empty|blank|null|missing|unpopulated)|"
    r"todav[ií]a (?:no muestra|no aparece|est[aá] vac[ií]o)|"
    r"no (?:aparece|se ve|muestra nada) (?:en pantalla|en la tarjeta|todav[ií]a)|"
    r"nothing (?:renders|shows|is displayed|appears on)"
    r")\b",
    re.IGNORECASE,
)

REMINDER = """ALMOST - ONE PART IS STILL EMPTY

{items}

The mechanism works and you proved it. The part you named as empty is the only thing between this and something a user can look at. Fill it, then the claim is fully yours."""


def evidence(message):
    works = WORKS.search(message)
    hollow = []
    for match in HOLLOW.finditer(message):
        found = match.group(0)
        if found.lower() not in [h.lower() for h in hollow]:
            hollow.append(found)
    if not works or not hollow:
        return []
    return [f"  - it reports: {works.group(0)}",
            "  - still open: " + ", ".join(hollow[:4])]


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("stop_hook_active"):
        return 0

    transcript = payload.get("transcript_path") or ""
    if not transcript or not os.path.exists(transcript):
        return 0

    raw = perm.last_assistant_text(transcript)
    if not raw:
        return 0
    message = perm.unquoted(raw)

    hits = evidence(message)
    if not hits:
        return 0

    sys.stderr.write(REMINDER.format(items="\n".join(hits)) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
