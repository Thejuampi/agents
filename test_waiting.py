#!/usr/bin/env python3
"""Waiting on launched work is not a reason to hold the turn open.

It used to be an exemption: work in flight, no pattern raised, turn allowed.
Measured over the transcripts, 56 turns took that pass and 12 of them ended
with the developer having to push - 21% against a base rate of 14%. The
exemption was releasing turns worse than average.

So waiting excuses nothing now. It selects a different ask: the work reports
back on its own, so spend the wait on the next piece.
"""
import json
import os
import subprocess
import sys
import tempfile

import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "perm", os.path.join(HERE, "check-permission.py"))
perm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(perm)
HOOK = os.path.join(HERE, "check-stop.py")

RUNS = []

WAIT = ("The fixed build is installed and running with a 7-minute RSS profile. "
        "I will report the outcome when the profiler ends.")


def counted():
    RUNS.append(None)


def fire(reply, launched=None, landed=False, asked="segui"):
    counted()
    NL = "\n"
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8")
    with handle:
        handle.write(json.dumps({"type": "user",
                                 "message": {"content": asked}}) + NL)
        if launched:
            name, extra = launched
            handle.write(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "bg1", "name": name,
                 "input": extra}]}}) + NL)
            if landed:
                handle.write(json.dumps({"type": "user", "message": {"content": [
                    {"type": "text", "text": "<task-notification>"
                     "<tool-use-id>bg1</tool-use-id>"
                     "</task-notification>"}]}}) + NL)
        else:
            handle.write(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Read",
                 "input": {}}]}}) + NL)
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": reply}]}}) + NL)
    state = handle.name + ".state"
    done = subprocess.run([sys.executable, HOOK],
                          input=json.dumps({"transcript_path": handle.name,
                                            "cwd": HERE,
                                            "stop_hook_active": False}),
                          capture_output=True, text=True,
                          env=dict(os.environ, STOP_STATE=state, STOP_LOG=state + ".log"), timeout=200)
    os.unlink(handle.name)
    if os.path.exists(state):
        os.unlink(state)
    return done.returncode, done.stderr


def main():
    failures = []

    code, err = fire(WAIT, launched=("Agent", {"description": "profile"}))
    if "REPORTS BACK ON ITS OWN" not in err:
        failures.append(f"waiting must ask for the next piece: {err[:140]}")

    code, err = fire(WAIT, launched=("Bash", {"command": "./gradlew test",
                                              "run_in_background": True}))
    if "REPORTS BACK ON ITS OWN" not in err:
        failures.append(f"a backgrounded command counts as launched: {err[:140]}")

    code, err = fire(WAIT)
    if "REPORTS BACK ON ITS OWN" in err:
        failures.append("nothing was launched, so nothing reports back")

    code, err = fire(WAIT, launched=("Agent", {"description": "profile"}),
                     landed=True)
    if "REPORTS BACK ON ITS OWN" in err:
        failures.append("work that already reported back is not still waiting")

    code, _ = fire("Anda todo. Manana sigo con el grafico.",
                   launched=("Agent", {"description": "profile"}))
    if code == 0:
        failures.append("deferred work must still block while a task runs")

    code, _ = fire("Listo. Waiting for your confirmation to merge.",
                   launched=("Agent", {"description": "review"}))
    if code == 0:
        failures.append("waiting on the user is a stop even with a task running")

    code, err = fire("API Error: Sonnet 5's safeguards flagged this message.")
    if code != 0:
        failures.append(f"a harness error page is not a stop: {err[:140]}")

    code, err = fire("You've hit your session limit - resets 11pm "
                     "(America/New_York)")
    if code != 0:
        failures.append(f"a usage limit notice is not a stop: {err[:140]}")

    counted()
    if not perm.offenders("Still running, nothing to report yet."):
        failures.append("an idle report is a pattern hit whatever is running")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
