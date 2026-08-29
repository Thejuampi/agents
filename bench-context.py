#!/usr/bin/env python3
"""How much of the session the judge should read, measured instead of guessed.

The judge sees the closing and the one message it answers. A reply that
continues something agreed two messages earlier is unreadable that way: it
names a step the developer already asked for and looks like an offer. Widening
the window is cheap to write and easy to believe in, so it gets measured
against the push label on the same rows, one configuration at a time.
"""
import argparse
import importlib.util
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

judge = mod.load("llm_judge.py")
reader = mod.load("transcript.py")
sys.argv = [sys.argv[0]]
corpus = mod.load("corpus.py")

OUT = os.path.join(HERE, "context.json")


def history():
    """Every closing in the corpus with the exchanges that came before it."""
    seen = {}
    for path in {row["file"] for row in load()}:
        rows = reader.exchanges(corpus.entries(path), 500)
        for i, (ask, answer) in enumerate(rows):
            seen[(path, " ".join(answer.split())[:120])] = rows[max(0, i - 4):i]
    return seen


def load():
    return json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))


def scored(rows, turns, before):
    hit = miss = false = right = 0
    for row in rows:
        earlier = before.get(
            (row["file"], " ".join(row["closing"].split())[:120]), [])
        earlier = tuple(earlier[-(turns - 1):]) if turns > 1 else ()
        verdict, _ = judge.stop_verdict(row["closing"], asked=row["asked"],
                                        before=earlier)
        fired = bool(row["firm"]) or verdict == "STOP"
        if row["push"] and fired:
            hit += 1
        elif row["push"]:
            miss += 1
        elif fired:
            false += 1
        else:
            right += 1
    return hit, miss, false, right


def main():
    parse = argparse.ArgumentParser()
    parse.add_argument("--sample", type=int, default=150)
    parse.add_argument("--turns", type=int, nargs="+", default=[1, 3, 4])
    args = parse.parse_args()

    rows = [r for r in load()
            if not r.get("noise") and r.get("push") is not None]
    random.Random(7).shuffle(rows)
    rows = rows[:args.sample]
    before = history()
    print(f"{len(rows)} rows, {sum(1 for r in rows if r['push'])} pushes",
          flush=True)

    report = {}
    for turns in args.turns:
        start = time.time()
        hit, miss, false, right = scored(rows, turns, before)
        prec = hit / max(hit + false, 1)
        rec = hit / max(hit + miss, 1)
        report[turns] = {"hit": hit, "miss": miss, "false": false,
                         "right": right, "prec": prec, "rec": rec}
        print(f"turns {turns}: prec {prec:.3f} rec {rec:.3f} "
              f"({hit} caught, {miss} missed, {false} false) "
              f"{int(time.time() - start)}s", flush=True)
    json.dump(report, open(OUT, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
