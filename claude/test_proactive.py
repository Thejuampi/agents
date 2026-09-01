#!/usr/bin/env python3
"""A clean closing gets one more question before the turn ends.

The judge answering OK used to end the turn by itself. It only ever asked
whether the agent stopped early, so a turn with nothing wrong in it was a turn
with nothing left to do. Those are different questions.

So OK no longer closes anything on its own. It asks once whether a next action
exists, and releases on the pass after that: the turn ends when the worker
looked and could not name one."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_live = importlib.util.spec_from_file_location(
    "_hook_live", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "live.py"))
live = importlib.util.module_from_spec(_live)
_live.loader.exec_module(live)

if not live.wanted():
    live.skip()

_settle = importlib.util.spec_from_file_location(
    "_hook_settle", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "settle.py"))
settle = importlib.util.module_from_spec(_settle)
_settle.loader.exec_module(settle)

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")


HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-stop.py")

_spec = importlib.util.spec_from_file_location("gate", HOOK)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

RUNS = []

DONE = ("The negation guard is in. Over 854 closings 37 change labels and 3"
        " were real pushes; the 19 that lose every firm label still reach the"
        " judge. Suite green, 19 files. Commit 3eaa2a6.")

NOTHING = ("I checked the callers, the tests and the docs for this path."
           " Every one already covers the new behaviour, so nothing remains.")


def transcript(reply, launched=None, asked="segui"):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8")
    with handle:
        handle.write(json.dumps({"type": "user",
                                 "message": {"content": asked}}) + "\n")
        name, extra = launched or ("Read", {})
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": name,
             "input": extra}]}}) + "\n")
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": reply}]}}) + "\n")
    return handle.name


def fire(path, state, again=False):
    RUNS.append(None)
    done = settle.run([sys.executable, HOOK],
                          input=json.dumps({"transcript_path": path,
                                            "cwd": HERE,
                                            "stop_hook_active": again}),
                          capture_output=True, text=True,
                          env=dict(os.environ, STOP_STATE=state,
                                   STOP_LOG=state + ".log"), timeout=200)
    return done.returncode, done.stderr


def extend(path, reply):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": reply}]}}) + "\n")


WROTE = ("Write", {"file_path": "guard.py", "content": "x"})


def chain(first, second, launched=None):
    """One session, one transcript: the ask and the answer it earned."""
    state = tempfile.NamedTemporaryFile(suffix=".state", delete=False).name
    os.unlink(state)
    path = transcript(first, launched)
    out = [fire(path, state)]
    extend(path, second)
    out.append(fire(path, state, again=True))
    os.unlink(path)
    if os.path.exists(state):
        os.unlink(state)
    return out


def main():
    failures = []

    (code, err), (after, _) = chain(DONE, NOTHING, WROTE)
    if "PROACTIVELY" not in err:
        failures.append(f"a clean closing must be asked once: {err[:140]}")
    if code != 2:
        failures.append(f"the ask has to block, exit {code}")
    if after != 0:
        failures.append(f"an answered ask must release, exit {after}")

    (_, first), (_, second) = chain(DONE, DONE, WROTE)
    if "PROACTIVELY" in second:
        failures.append("the ask fires once per chain, never twice")

    _, err = fire(transcript(
        "The fixed build runs a 7-minute RSS profile. I report when it ends.",
        ("Agent", {"description": "profile"})),
        tempfile.NamedTemporaryFile(suffix=".s", delete=False).name)
    if "REPORTS BACK ON ITS OWN" not in err:
        failures.append(f"work in flight keeps its own ask: {err[:140]}")

    _, err = fire(transcript("Anda todo. Manana sigo con el grafico."),
                  tempfile.NamedTemporaryFile(suffix=".s", delete=False).name)
    if "PROACTIVELY" in err:
        failures.append("deferred work is a stop, not a clean closing")

    code, _ = fire(transcript("API Error: request timed out."),
                   tempfile.NamedTemporaryFile(suffix=".s", delete=False).name)
    if code != 0:
        failures.append("a harness error page is never asked anything")

    code, err = fire(transcript(DONE), tempfile.NamedTemporaryFile(
        suffix=".s", delete=False).name)
    if code != 0:
        failures.append("a clean closing with nothing to name must release")

    RUNS.append(None)
    path = transcript(DONE, WROTE)
    extend(path, NOTHING)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "user", "message": {
            "content": "Stop hook feedback: KEEP GOING"}}) + "\n")
    if gate.last_user(path) != "segui":
        failures.append("the judge must be told what the developer asked, not what the gate said")
    os.unlink(path)

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
