#!/usr/bin/env python3
"""A closing that names the next step is a stop, not a report.

The gate already reads whether the turn left code untested or docs stale, and
whether a background task is still running. Neither of those sees the failure
that actually happens most: the turn does real work, ships it with tests, and
then ends on "next I'll do X" - with X sitting there, unstarted, already
permitted, and cheaper to do than to announce.

That closing passed every lane. The judge scored it OK at 0.773 because
nothing in it was wrong; it was a good turn. The proactive lane had nothing to
point at because the turn had written its tests and touched a doc, which is
exactly what a clean turn looks like. Both lanes measured the quality of what
was done and neither asked whether the sentence at the end was an order the
agent had written for itself and not executed.

This reads that sentence. Only the tail, because an intention stated mid-message
is context and the same words at the end are where the work stopped.

It stands down when the turn is waiting on something outside itself. "Sigo
esperando el agente" is not a stop and the waiting lane already owns it.
"""
import importlib.util
import os
import re
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

MAYBE = 3
TAIL_LINES = 3

perm = mod.load("check-permission.py")

WAITING = re.compile(
    r"\b(?:esperando|espero|a la espera|quedo a la espera|"
    r"waiting (?:on|for)|blocked on|blocked by|once it (?:finishes|reports)|"
    r"cuando (?:termine|terminen|reporte|reporten|vuelva|vuelvan|est[eé]n?))\b",
    re.IGNORECASE)

HANDOFF = re.compile(
    r"(?:\?\s*$|\bcual (?:prefer|quer)|which (?:one )?do you|"
    r"\bdecid[ií]s vos\b|\btu llamada\b|\byour call\b|"
    r"\bsi quer[eé]s\b|\bsi quieres\b|\bsi te parece\b|\bcuando digas\b|"
    r"\bcuando quieras\b|\bavis[aá]me\b|\bsay the word\b|\bif you want\b|"
    r"\bjust tell me\b|\blet me know\b|\bconfirm[aá]s\b|hasta que confirmes)",
    re.IGNORECASE)

SURE = re.compile(
    r"(?:^|[.;:!\n]\s*|\*\*|\bahora\s+|\by\s+)"
    r"(?:sigo|continuo|continúo|arranco|empiezo|paso|voy|"
    r"me pongo|arrancamos|seguimos)"
    r"\s+(?:a\s+|con\s+|al\s+|ahora\s+)*"
    r"(?!esperando|a esperar|esperar)"
    r"[\w`áéíóúñ]"
    r"|\bnext(?:\s+up)?[,:]?\s+I\s*(?:(?:'|’)?ll|will)\b"
    r"|\bI\s*(?:(?:'|’)?ll|will)\s+(?:now\s+)?(?:continue|start|move|carry|do|write|"
    r"build|add|wire|implement|finish)\b"
    r"|\blet me\s+(?:now\s+)?(?:continue|start|keep going)\b"
    r"|\bmoving on to\b|\bnext step[s]?\s*[:,]|\bon to the\b",
    re.IGNORECASE)

WEAK = re.compile(
    r"\b(?:pendiente[s]?|por hacer|me falta|nos falta|"
    r"still to do|still pending|remaining work|not yet (?:wired|done|written))\b",
    re.IGNORECASE)

REMINDER = """KEEP GOING - YOU NAMED THE NEXT STEP INSTEAD OF TAKING IT

Your closing says: "{quote}"

That sentence is a work order you wrote for yourself and did not run. Permission was already granted and it does not expire. Doing it costs less than announcing it.

Take it now, in this turn. Come back when it is done, or when you hit something only the developer can decide."""

SOFT = """ALMOST - YOU LEFT SOMETHING NAMED AND UNSTARTED

Your closing says: "{quote}"

If that work is yours and nothing blocks it, do it now rather than hand it back. If it genuinely belongs to the developer, say so in one line and name what you need."""


FENCE = re.compile(r"```.*?```", re.S)


def plain(message):
    """Fenced code out, inline backticks off.

    perm.unquoted strips what is inside backticks, and an announcement names
    its object in backticks more often than not: "sigo con `query`, `store`"
    came back as "sigo con , " and matched nothing. The fence is the part that
    can hide a stray sentence; the inline tick is the object itself."""
    return FENCE.sub(" ", message or "").replace("`", "")


def tail_of(message):
    lines = [line.strip() for line in plain(message).splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    return " ".join(lines[-TAIL_LINES:])


def quote_of(tail, match):
    start = max(0, match.start() - 20)
    text = tail[start:match.start() + 140].strip()
    return re.sub(r"\s+", " ", text)


SPLIT = re.compile(r"(?<=[.!?:])\s+|\n+")


def sentences(tail):
    return [part.strip() for part in SPLIT.split(tail) if part.strip()]


def verdict(message):
    tail = tail_of(message)
    parts = sentences(tail)
    if not parts:
        return 0, ""
    if WAITING.search(parts[-1]) or HANDOFF.search(parts[-1]):
        return 0, ""
    soft = None
    for part in parts:
        if WAITING.search(part) or HANDOFF.search(part):
            continue
        hit = SURE.search(part)
        if hit:
            return 2, REMINDER.format(quote=quote_of(part, hit))
        if soft is None:
            hit = WEAK.search(part)
            if hit:
                soft = SOFT.format(quote=quote_of(part, hit))
    if soft:
        return MAYBE, soft
    return 0, ""


def main():
    import json
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("stop_hook_active"):
        return 0
    code, text = verdict(perm.closing_of(payload))
    if code:
        sys.stderr.write(text + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
