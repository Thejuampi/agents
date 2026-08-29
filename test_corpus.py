#!/usr/bin/env python3
"""The corpus must never hand the gate its own words to grade.

A block wakes the agent through a plain user string. Read as the developer
speaking it corrupts the label twice: the push judge scores the gate's own
reminder, and the window closes at the block, so work the agent did after
being woken is credited to a closing that never earned it.

The first build had 120 of 854 pairs in that state and 9 of its 123 positives
were the gate scoring itself."""
import importlib.util
import os
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

HERE = os.path.dirname(os.path.abspath(__file__))

corpus = mod.load("corpus.py")

WAKE = {"type": "user", "message": {"content":
        "Stop hook feedback: KEEP GOING - THERE LOOKS TO BE WORK LEFT"}}
REAL = {"type": "user", "message": {"content": "segui con el resto"}}
RESULT = {"type": "user", "message": {"content": [
          {"type": "tool_result", "content": "ok"}]}}


def main():
    failures = []
    cases = 0

    cases += 1
    if corpus.spoke(WAKE):
        failures.append("the gate's own wake is not the developer")

    cases += 1
    if not corpus.spoke(REAL):
        failures.append("a real user message still counts")

    cases += 1
    if corpus.spoke(RESULT):
        failures.append("a tool result wears the user role and is not the user")

    cases += 1
    if corpus.spoke({"type": "assistant", "message": {"content": "hi"}}):
        failures.append("the agent is not the developer")

    cases += 1
    if corpus.reply_of(
            "[Image: original 1080x2400, displayed at 900x2000.]") is not None:
        failures.append("a screenshot with no words is not a reply")

    cases += 1
    if corpus.reply_of("[Image #2] esta vacia, arreglalo") != "esta vacia, arreglalo":
        failures.append("words next to a screenshot are still the reply")

    cases += 1
    if corpus.reply_of("[Request interrupted by user]") is not None:
        failures.append("an escape is not the developer writing")

    cases += 1
    if corpus.reply_of("seguí con el resto") != "seguí con el resto":
        failures.append("a plain reply survives untouched")

    print(f"{cases} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
