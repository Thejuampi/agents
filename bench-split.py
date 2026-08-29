#!/usr/bin/env python3
"""Does tuning on this corpus transfer to sessions it never saw?

Every class demotion in this work was chosen by searching the same rows it is
reported on. This splits the corpus by session, runs the search on one half
and scores the choice on the other, and repeats. Offline: it reads the stored
labels and calls no model."""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPLITS = 20


def rows(path):
    data = json.load(open(path, encoding="utf-8"))
    return [r for r in data if not r.get("noise")]


def firm_of(row, off):
    return [h for h in (row.get("firm") or [])
            if h.split(":")[0].rstrip() not in off]


def precision(part, off):
    fired = [r for r in part
             if firm_of(r, off) or r.get("verdict") == "STOP"]
    caught = sum(1 for r in fired if r.get("push"))
    return len(fired), caught / max(len(fired), 1)


def names(part):
    found = set()
    for row in part:
        for hit in row.get("firm") or []:
            found.add(hit.split(":")[0].rstrip())
    return found


def greedy(part):
    off, best = set(), precision(part, set())[1]
    while True:
        moved = None
        for name in names(part) - off:
            got = precision(part, off | {name})[1]
            if got > best:
                moved, best = name, got
        if not moved:
            return off
        off.add(moved)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    real = rows(os.path.join(HERE, "corpus.json"))
    files = sorted({r["file"] for r in real})
    print(len(files), "sessions,", len(real), "closings")
    random.seed(7)
    gains = []
    for _ in range(SPLITS):
        order = files[:]
        random.shuffle(order)
        half = set(order[:len(order) // 2])
        fit = [r for r in real if r["file"] in half]
        held = [r for r in real if r["file"] not in half]
        if not fit or not held:
            continue
        off = greedy(fit)
        before = precision(held, set())[1]
        after = precision(held, off)[1]
        gains.append(after - before)
        print(f"demote {len(off)}: held-out {before:.3f} -> {after:.3f}")
    up = sum(1 for g in gains if g > 0)
    print(f"mean held-out gain {sum(gains) / len(gains):+.4f} over {len(gains)}"
          f" splits, positive in {up}")


if __name__ == "__main__":
    main()
