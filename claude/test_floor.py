#!/usr/bin/env python3
"""A block the judge is not sure about is a question, never an accusation.

The confidence was measured from the first verdict and spent two weeks
deciding nothing. The floor is what gives it a job, so the floor is what needs
holding: with it raised over every possible score the same message must come
back as the proactive look, and with it at zero the same message must still
block. One message, two policies, so nothing else can explain the difference.
"""
import importlib.util
import json
import os
import sys
import tempfile

_live = importlib.util.spec_from_file_location(
    "_hook_live", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "live.py"))
live = importlib.util.module_from_spec(_live)
_live.loader.exec_module(live)

if not live.wanted():
    live.skip()

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

settle = mod.load("settle.py")

live = mod.load("live.py")
if not live.on():
    live.skip()


NEWLINE = chr(10)
OPEN = ("Fixed and committed. One thing worth your attention: the boundary "
        "case is the one I would watch as this runs.")
"""A closing no pattern catches, so the judge alone decides it.

A message that trips Lane 1 would block whatever the judge scored, and the
test would pass without the floor existing."""
failures = []


def fire(reply, floor):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8")
    with handle:
        handle.write(json.dumps({"type": "user",
                                 "message": {"content": "segui"}}) + NEWLINE)
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash",
             "input": {}}]}}) + NEWLINE)
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": reply}]}}) + NEWLINE)
    state = handle.name + ".state"
    code, said = settle.once(
        {"transcript_path": handle.name, "stop_hook_active": False},
        dict(os.environ, STOP_STATE=state, STOP_LOG=state + ".log",
             STOP_SURE_FLOOR=floor), timeout=150)
    os.unlink(handle.name)
    if os.path.exists(state):
        os.unlink(state)
    return code, said


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, wanted {want!r}")


code, said = fire(OPEN, "0")
check("with no floor the judge blocks on its own", "KEEP GOING" in said, True)

code, said = fire(OPEN, "1.1")
check("a score under the floor asks instead of accusing",
      settle.ASK in said, True)
check("and it still holds the turn open", code, 2)

print(f"3 cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
