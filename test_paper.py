#!/usr/bin/env python3
"""The paper counts things the repo can count for itself.

Every number here was written by hand once and went stale the first time a
pattern was added. A claim about the code belongs in a test, so the suite
fails instead of the reader finding it."""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ("paper-head.tex", "paper-body.tex", "paper-appendix.tex",
         "paper-results.tex")
COUNTED = (r"(\d{3}) (?:regular expressions|pattern labeling functions"
           r"|patterns are grouped)")


def load(alias, filename):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perm = load("perm", "check-permission.py")


def tex():
    out = []
    for name in FILES:
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            out.append((name, open(path, encoding="utf-8").read()))
    return out


def corpus():
    path = os.path.join(HERE, "corpus.json")
    if not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    return [r for r in data if not r.get("noise")]


def main():
    failures = []
    cases = 0
    patterns = perm.patterns_for(HERE)
    total = len(patterns)
    doubts = sum(1 for label, _ in patterns if perm.weak(label))

    cases += 1
    for name, body in tex():
        said = {int(n) for n in re.findall(COUNTED, body)}
        if said and said != {total}:
            failures.append(f"{name} counts {sorted(said)}, repo has {total}")

    cases += 1
    splits = []
    for name, body in tex():
        splits += [[int(n) for n in hit]
                   for hit in re.findall(r"(\d+) of the (\d+) are firm", body)]
        splits += [[int(n) for n in hit] for hit in re.findall(
            r"Of (\d+) patterns, (\d+) are firm and (\d+) are doubts", body)]
    for claim in splits:
        want = ([total - doubts, total] if len(claim) == 2
                else [total, total - doubts, doubts])
        if claim != want:
            failures.append(f"the firm split says {claim}, repo has {want}")

    cases += 1
    if not splits:
        failures.append("the paper stopped stating the firm split")

    cases += 1
    for name, body in tex():
        for line in body.splitlines():
            if line.startswith("ef{") or line.startswith("extt"):
                failures.append(f"{name} carries a broken macro: {line[:40]}")

    rows = corpus()
    pushes = sum(1 for r in rows if r.get("push"))
    results = dict(tex()).get("paper-results.tex", "")

    cases += 1
    if rows and str(len(rows)) not in results:
        failures.append(f"the results never state the corpus size {len(rows)}")

    cases += 1
    if rows and str(pushes) not in results:
        failures.append(f"the results never state the push count {pushes}")

    print(f"{cases} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
