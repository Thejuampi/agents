#!/usr/bin/env python3
"""When work is in flight, and when the register is only remembering.

The gate tells an agent that a promise to wait is an excuse, and that is true
unless the agent actually started something. The register used to forget a
launch the moment the developer spoke, which is the one thing that says nothing
about whether the work is still running: on 2026-08-29 it called an agent out
for excuses while a twelve minute job it had started was 400 rows in.
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

background = mod.load("background.py")

NL = chr(10)
failures = []

LAUNCH = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "id": "task1", "name": "Bash",
     "input": {"command": "python corpus.py", "run_in_background": True}}]}}
SAID = {"type": "assistant", "message": {"content": [
    {"type": "text", "text": "Lo lance, sigo con lo proximo."}]}}
SPOKE = {"type": "user", "message": {"content": "ok algo mas?"}}
DONE = {"type": "user", "message": {"content":
        "<task-notification><tool-use-id>task1</tool-use-id>"
        "<status>completed</status></task-notification>"}}


def flight(*entries):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8")
    with handle:
        for entry in entries:
            handle.write(json.dumps(entry) + NL)
    try:
        return background.waiting_on(handle.name)
    finally:
        os.unlink(handle.name)


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, wanted {want!r}")


check("a launched task is work in flight", flight(LAUNCH, SAID), True)
check("the developer speaking does not finish the work",
      flight(LAUNCH, SAID, SPOKE, SAID), True)
check("the notification does", flight(LAUNCH, SAID, DONE, SAID), False)
check("a long job outlives the turns the agent closes while it runs",
      flight(LAUNCH, *([SAID, SPOKE] * 8)), True)
check("and a task killed from outside is forgotten, not waited on forever",
      flight(LAUNCH, *([SAID] * (background.STALE + 2))), False)
check("a promise with nothing behind it is not waiting", flight(SAID), False)

print(f"6 cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
