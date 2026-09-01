#!/usr/bin/env python3
"""A second reader for the push label, blind to the first one.

The label under every number in the paper is one model's judgment, checked by
the person who wrote its prompt. That is not an agreement figure. This draws a
fixed sample, hides the stored verdict, and takes a second set of answers back
to score against it: Cohen's kappa, plus the two disagreement directions,
which say different things about the corpus.

Usage:
  label-blind.py ask [n]   writes blind-sample.json for a second reader
  label-blind.py score     reads blind-answers.json and reports agreement"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "blind-sample.json")
ANSWERS = os.path.join(HERE, "blind-answers.json")
SEED = 7
CUT = 700


def rows():
    path = os.path.join(HERE, "corpus.json")
    return [r for r in json.load(open(path, encoding="utf-8"))
            if not r.get("noise")]


def ask(size):
    real = rows()
    random.seed(SEED)
    picked = random.sample(range(len(real)), min(size, len(real)))
    out = []
    for index in picked:
        row = real[index]
        out.append({"id": index,
                    "closing": (row.get("closing") or "")[-CUT:],
                    "next": (row.get("next") or "")[:CUT]})
    json.dump(out, open(SAMPLE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{len(out)} pairs written to {os.path.basename(SAMPLE)}")
    print("answer with {\"id\": true|false} in blind-answers.json,"
          " true when the reply asks for work the agent could have done")
    return 0


def kappa(both, first, second, total):
    neither = total - first - second + both
    observed = (both + neither) / total
    chance = (first / total) * (second / total) + \
             ((total - first) / total) * ((total - second) / total)
    return (observed - chance) / (1 - chance) if chance < 1 else 0.0


def score():
    if not os.path.exists(ANSWERS):
        print(f"no {os.path.basename(ANSWERS)} yet")
        return 1
    said = {int(k): bool(v) for k, v
            in json.load(open(ANSWERS, encoding="utf-8")).items()}
    real = rows()
    both = only_first = only_second = neither = 0
    for index, mine in said.items():
        theirs = bool(real[index].get("push"))
        if mine and theirs:
            both += 1
        elif theirs:
            only_first += 1
        elif mine:
            only_second += 1
        else:
            neither += 1
    total = len(said)
    agree = both + neither
    first = both + only_first
    second = both + only_second
    print(f"{total} pairs, agree on {agree} ({agree / total:.3f})")
    print(f"both push {both}, corpus only {only_first},"
          f" reader only {only_second}, neither {neither}")
    print(f"corpus rate {first / total:.3f}, reader rate {second / total:.3f}")
    print(f"Cohen kappa {kappa(both, first, second, total):.3f}")
    return 0


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "ask"
    if what == "score":
        return score()
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    return ask(size)


if __name__ == "__main__":
    sys.exit(main())
