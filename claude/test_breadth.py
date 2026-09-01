#!/usr/bin/env python3
"""A pattern wide enough to match ordinary prose makes the hook cry wolf, and
a hook that cries wolf gets ignored. This fails the suite before that lands.

The bar is deliberately loose. Some phrases are genuinely ambiguous - docs say
"if you want the full profile, run make"; an agent closing a turn with the same
words is asking permission. What must never pass is a pattern that matches
language itself.
"""
import importlib.util
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BREADTH_REPO", r"G:/dev/repos/discount_screener")
CEILING = 0.02


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(HERE, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


breadth = load("audit-breadth.py", "breadth")
perm = breadth.perm


def main():
    corpus = breadth.paragraphs(REPO)
    if not corpus:
        print(f"0 cases, 0 failures (no prose under {REPO})")
        return 0

    failures = []
    widest = (0, "")
    for label, compiled in perm.patterns_for(REPO):
        hits = sum(1 for text in corpus if compiled.search(perm.unquoted(text)))
        share = hits / len(corpus)
        if share > widest[0]:
            widest = (share, f"{label}: {compiled.pattern}")
        if share > CEILING:
            failures.append(f"{share:.1%} of prose matches {label}: {compiled.pattern}")

    print(f"{len(corpus)} paragraphs, widest {widest[0]:.1%} ({widest[1]}), "
          f"{len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
