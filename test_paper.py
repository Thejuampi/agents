#!/usr/bin/env python3
"""The paper counts things the repo can count for itself.

Every number here was written by hand once and went stale the first time a
pattern was added. A claim about the code belongs in a test, so the build
fails instead of the reader finding it."""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(alias, filename):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perm = load("perm", "check-permission.py")


def tex():
    out = []
    for name in ("paper-head.tex", "paper-body.tex", "paper-appendix.tex",
                 "paper-results.tex"):
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            out.append((name, open(path, encoding="utf-8").read()))
    return out


def main():
    failures = []
    cases = 0
    patterns = perm.patterns_for(HERE)
    total = len(patterns)
    doubts = sum(1 for label, _ in patterns if perm.weak(label))

    cases += 1
    stale = [name for name, body in tex()
             if re.search(r"[^0-9](\d{3}) (?:regular expressions|pattern"
                          r" labeling functions|patterns are grouped)", body)
             and str(total) not in re.findall(
                 r"[^0-9](\d{3}) (?:regular expressions|pattern labeling"
                 r" functions|patterns are grouped)", body)]
    if stale:
        failures.append(f"the pattern count is stale in {stale}, repo has {total}")

    cases += 1
    said = []
    for name, body in tex():
        said += re.findall(r"(\d+) of the (\d+) are firm", body)
        said += re.findall(r"Of (\d+) patterns, (\d+) are firm and (\d+) are doubts",
                           body)
    for claim in said:
        numbers = [int(n) for n in claim]
        if len(numbers) == 2 and numbers != [total - doubts, total]:
            failures.append(f"firm split {numbers} against {[total - doubts, total]}")
        if len(numbers) == 3 and numbers != [total, total - doubts, doubts]:
            failures.append(
                f"firm split {numbers} against {[total, total - doubts, doubts]}")

    cases += 1
    if not said:
        failures.append("the paper stopped stating the firm split")

    print(f"{cases} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
