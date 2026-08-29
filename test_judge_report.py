#!/usr/bin/env python3
"""A block is graded by what the agent did next, not by what it said."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

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

report = mod.load("judge-report.py")

RUNS = []


def counted():
    """A case counts itself, so adding one never leaves the total lying."""
    RUNS.append(None)


def said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def used(times):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {}} for _ in range(times)]}}


def asked(text):
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def result():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}


def transcript(rows):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for row in rows:
        handle.write(json.dumps(row) + "\n")
    handle.close()
    return handle.name


def graded(rows, head):
    counted()
    path = transcript(rows)
    did = report.after(report.turns(path), head)
    os.unlink(path)
    return did


def brief_over(blocks, tools, twice=False):
    """Runs the session-start brief over a log built for this case."""
    rows = [said("falta el commit")] + ([used(tools)] if tools else [])
    path = transcript(rows)
    log = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for _ in range(blocks):
        log.write(json.dumps({"lane": "pattern", "file": path, "head": "falta el commit",
                              "firm": ["Matched: ask: querés que"]}) + chr(10))
    log.close()
    env = dict(os.environ, STOP_LOG=log.name, PYTHONIOENCODING="utf-8")
    hook = os.path.join(HERE, "judge-report.py")
    if twice:
        settle.run([sys.executable, hook, "--brief"], env=env, capture_output=True)
    done = settle.run([sys.executable, hook, "--brief"], env=env,
                          capture_output=True, text=True)
    os.unlink(path)
    os.unlink(log.name)
    return done.stdout.strip()


def main():
    failures = []

    if graded([said("falta el commit"), used(4), said("listo")], "falta el commit") != 4:
        failures.append("tool calls after a block must count as work bought")

    if graded([said("falta el commit"), said("ya te expliqué")], "falta el commit") != 0:
        failures.append("another paragraph buys nothing")

    if graded([said("falta el commit"), asked("dale"), used(9)], "falta el commit") != 0:
        failures.append("work after the user spoke again is not the block's doing")

    if graded([said("falta el commit"), used(2), result(), used(3)], "falta el commit") != 5:
        failures.append("a tool result is not the user speaking")

    if graded([said("otra cosa")], "falta el commit") is not None:
        failures.append("a message that is not in the transcript cannot be graded")

    counted()
    names = report.classes({"weak": ["KEEP GOING\n\nMatched: announce?: falta, wait: i'll wait. "
                                     "What you did is fine and permission was granted"]})
    if names != ["announce?", "wait"]:
        failures.append(f"the pattern classes must come off the Matched line: {names}")

    counted()
    if report.classes({"verdict": "STOP"}) != ["judge"]:
        failures.append("a block with no pattern belongs to the judge")

    counted()
    if report.spoke(result()):
        failures.append("a tool result must never read as the user")

    counted()
    if report.ripe_ones({"ask": [0] * 7}):
        failures.append("seven blocks are not enough evidence to demote")

    counted()
    if report.ripe_ones({"ask": [0] * 8}) != [("ask", [0] * 8)]:
        failures.append("eight blocks that bought nothing must name the pattern")

    counted()
    if report.ripe_ones({"ask": [9] * 8}):
        failures.append("a pattern whose blocks bought work must never be demoted")

    counted()
    body = brief_over(8, tools=0)
    if "ask" not in body:
        failures.append(f"a ripe pattern must be named at session start: {body!r}")

    counted()
    if brief_over(8, tools=0, twice=True):
        failures.append("the same news must not be repeated the same day")

    counted()
    if brief_over(8, tools=9):
        failures.append("blocks that bought work must keep the brief quiet")

    counted()
    if report.classes({"waiting": True,
                       "firm": ["Matched: ask: querés que"]}) != ["waiting"]:
        failures.append("a block sent while work runs is graded as its own class")

    counted()
    if report.classes({"ask": True, "verdict": "OK"}) != ["proactive"]:
        failures.append("the question an OK earns is graded on its own")

    counted()
    if not report.classes({"verdict": "OK", "ask": False}):
        failures.append("a released OK still falls back to a class")

    counted()
    if report.classes({"firm": [
            "Matched: ask: queres que, README.md, AGENTS.md"]}) != ["ask"]:
        failures.append("a file the reminder quotes is not a class")

    counted()
    woken = [
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Listo, no queda nada."}]}},
        {"type": "user", "message": {"content":
            "Stop hook feedback: KEEP GOING - YOU ALREADY HAVE PERMISSION"}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "Edit", "input": {}},
            {"type": "tool_use", "id": "b", "name": "Bash", "input": {}}]}},
    ]
    if report.after(woken, "Listo, no queda nada.") != 2:
        failures.append("the gate's own wake must not close the window it is graded in")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
