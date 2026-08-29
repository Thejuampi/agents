#!/usr/bin/env python3
"""Puts the local model to work where it is actually good: finding candidates.

It has recall and no precision, so it is wrong to let it block a turn. It is
right to let it read every closing message the pattern list ignores and hand
back the ones worth a human look. The patterns that survive that look are what
goes into stop-patterns.txt, and those cost nothing at run time.

Usage: mine-stops.py [model] [--limit N] [--tail N]
"""
import importlib.util
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(HERE, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bench = load("bench-llm.py", "bench")
judge = bench.judge


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        judge.MODEL = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 80
    tail = int(sys.argv[sys.argv.index("--tail") + 1]) if "--tail" in sys.argv else 400

    original = judge.messages

    def shortened(message):
        return original(message[-tail:])

    judge.messages = shortened

    _, _, quiet = bench.collect()
    flagged = []
    for text in quiet[:limit]:
        label, _ = judge.verdict(text)
        if label == "STOP":
            flagged.append(text)

    judge.messages = original
    print(f"{judge.MODEL}: {len(flagged)} of {len(quiet[:limit])} unmatched closings "
          f"look like stops\n")
    for text in flagged:
        print("=" * 70)
        print(text[-500:].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
