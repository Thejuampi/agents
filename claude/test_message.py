#!/usr/bin/env python3
"""A block message the agent will not read is a block that does nothing.

Every template grew by one clarifying sentence at a time until the shortest of
them ran past a screen. The budget below is the size each message was cut to
once, so the next sentence added has to displace one already there."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET = {
    "REPEAT": 20, "SAME": 20, "PHRASE": 45, "NO_PHRASE": 60, "FAKE": 50,
    "QUOTE": 15, "SILENT": 35, "LLM_STOP": 45, "WAITING": 45, "NEAR": 45,
    "PROACTIVE": 75,
}
BANNED = ("You are more than able", "nobody can argue", "the turn closes",
          "What you did is fine")


def load(alias, filename):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    stop = load("stop", "check-stop.py")
    perm = load("perm", "check-permission.py")
    cases = 0
    failures = []

    for name, budget in sorted(BUDGET.items()):
        cases += 1
        words = len(getattr(stop, name).split())
        if words > budget:
            failures.append(f"{name} runs {words} words over a budget of {budget}")

    cases += 1
    words = len(perm.REMINDER.split())
    if words > 55:
        failures.append(f"REMINDER runs {words} words over a budget of 55")

    texts = [getattr(stop, name) for name in BUDGET] + [perm.REMINDER]
    for phrase in BANNED:
        cases += 1
        for text in texts:
            if phrase in text:
                failures.append(f"a message carries the padding {phrase!r}")
                break

    print(f"{cases} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
