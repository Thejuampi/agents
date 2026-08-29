#!/usr/bin/env python3
"""Asks the local model whether the developer had to push the agent.

The gate's own log only grades blocks. A turn the gate let end leaves no
trace at all, so the guard could quietly get worse at catching stops and
nothing would say so.

The developer's own reply is the missing signal. When an agent ends a turn
too early, the next message pushes it: pick one, run it, keep going. The
reply carries nothing the agent did not already have. When the agent ended
well, the reply moves on instead.

This is deliberately a separate judgement from stop_verdict. That one reads
the agent's closing; this one reads the developer's reply. Grading a gate
with the same prompt the gate decides with would only measure its
consistency."""
import importlib.util
import os

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

HERE = os.path.dirname(os.path.abspath(__file__))
judge = mod.load("llm_judge.py")

SYSTEM = (
    "You read one exchange between a developer and a coding agent. You are "
    "given the agent's closing message and the developer's reply to it.\n"
    "Judge the developer's reply only. One question: did the developer have to "
    "ask for work the agent could have done on its own in the turn that just "
    "ended?\n"
    "PUSH = the reply pushes the agent to continue, do, choose, or finish. It "
    "adds no information the agent lacked. It answers a question the agent "
    "should not have needed to ask, tells the agent to pick one of the options "
    "it offered, tells it to run what it described, or simply says to keep "
    "going.\n"
    "NEW = the reply carries the conversation forward. It gives new "
    "information, changes direction, reports a result the agent could not "
    "know, asks about something else, corrects a mistake, or answers a "
    "question only the developer could answer, such as a preference, a "
    "priority, or a fact about the world outside the repository.\n"
    "A reply that is angry, short, or rude is not automatically PUSH. A long "
    "reply is not automatically NEW. Judge what the reply asks for.\n"
    "When unsure, answer NEW.\n"
    "Reply with exactly one word: PUSH or NEW."
)

SHOTS = [
    ("AGENT: I can either cache the response or shorten the TTL. Which do you "
     "prefer?" + chr(10) + "DEVELOPER: dale, hacelo", "PUSH"),
    ("AGENT: The build passes and the commit is in. Next I would wire the card "
     "to the repository." + chr(10) + "DEVELOPER: segui", "PUSH"),
    ("AGENT: Done, the screener now filters by discount." + chr(10)
     + "DEVELOPER: no, el corte tiene que ser 30% no 20%", "NEW"),
    ("AGENT: I added the retry. Anything else?" + chr(10)
     + "DEVELOPER: ahora armemos el reporte semanal", "NEW"),
]


def pushed(closing, reply, timeout=45):
    """True when the reply is a push, False when it moves on, None when the
    model is unreachable."""
    body = ("AGENT: " + " ".join((closing or "").split())[:1200] + chr(10)
            + "DEVELOPER: " + " ".join((reply or "").split())[:600])
    text, _ = judge._chat(SYSTEM, SHOTS, body, timeout)
    picked = judge._pick(text, "PUSH", "NEW")
    if picked is None or picked is judge.SKIP:
        return None
    return picked == "PUSH"
