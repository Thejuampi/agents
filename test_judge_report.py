#!/usr/bin/env python3
"""A block is graded by what the agent did next, not by what it said."""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("report", os.path.join(HERE, "judge-report.py"))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

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

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
