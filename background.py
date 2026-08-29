#!/usr/bin/env python3
"""Work a turn started that reports back on its own.

Shared, because two lanes need the same fact and neither can import the other:
check-stop.py loads check-permission.py, so the detection cannot live in
either one.
"""
import importlib.util
import json
import os
import re

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

reader = mod.load("transcript.py")


def entries(transcript):
    try:
        with open(transcript, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


BACKGROUND = ("agent", "task", "monitor", "croncreate", "schedulewakeup")


STALE = 30
"""Closings a launch survives without its notification.

A task killed from outside the session never reports, and a register that
never forgets would answer "still waiting" for the rest of the day. The number
has to clear a long job: the twelve minute run that exposed this had the agent
close its turn eight times while the work was still going, and six was not
enough. Thirty is about an hour of dense work, and every task the harness
tracks reports back well before that."""


NOTIFIED = re.compile(r"<tool-use-id>\s*([^<\s]+)", re.IGNORECASE)


def waiting_on(transcript):
    """True when this turn started work that has not reported back yet.

    The harness re-invokes the session when a background task ends, so an
    agent that says it is waiting is describing the mechanism, not dodging.

    The developer speaking does not end it. It used to: any real user turn
    cleared the register, on the reasoning that a new request retires the old
    wait. It does not - the task keeps running and the harness still wakes the
    session for it - and on 2026-08-29 that told an agent it was making excuses
    while a 12 minute job it had started was 400 rows in. A launch ends when its
    notification arrives, or after STALE closings if that notification never
    does, which covers a task killed from outside the session.

    A launch is not enough and a missing tool_result is the wrong signal: a
    backgrounded call answers immediately with its task id, so that absence
    never happens and the first version of this measured zero. The end of the
    work arrives as its own <task-notification>, carrying the tool-use-id of
    the call that started it. Launch opens the wait, that notification closes
    it. Read from the tool calls either way - a promise to wait is cheap, a
    launched task is not."""
    live = {}
    for entry in entries(transcript):
        for key in [k for k, (_, age) in live.items() if age > STALE]:
            live.pop(key, None)
        kind = entry.get("type")
        content = entry.get("message", {}).get("content")
        if kind == "user":
            text = content if isinstance(content, str) else " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ) if isinstance(content, list) else ""
            for done in NOTIFIED.findall(text or ""):
                live.pop(done, None)
            continue
        if kind != "assistant" or not isinstance(content, list):
            continue
        if any(isinstance(b, dict) and b.get("type") == "text" and
               (b.get("text") or "").strip() for b in content):
            live = {k: (n, age + 1) for k, (n, age) in live.items()}
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = str(block.get("name") or "").lower()
            payload = block.get("input") or {}
            if name in BACKGROUND or payload.get("run_in_background") is True:
                live[block.get("id")] = (name, 0)
    return bool(live)


