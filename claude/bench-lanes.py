#!/usr/bin/env python3
"""Recomputes the lane and class ablations on whichever corpus is given.

Everything here reads the stored labels, so it runs offline and costs no
model calls. The tables in the paper were first computed on the contaminated
corpus; this reproduces them on the clean one."""
import json
import math
import os
import sys

from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))


MACHINE = ("<task-notification>", "<local-command-caveat>", "<command-name>",
           "<system-reminder>", "[Request interrupted",
           "Continue from where you left off")


def spoke(row):
    """Did the developer write the next message at all?

    The label reads the reply that follows a closing. On 38% of them nobody
    replied: the turn was resumed by a task notification, a hook, a slash
    command or a resume prompt. Those rows can carry a push only by accident,
    and leaving them in divides every precision by a denominator the developer
    never touched."""
    text = row.get("next") or ""
    return not any(mark in text for mark in MACHINE)


def rows(path, human=False):
    data = json.load(open(path, encoding="utf-8"))
    live = [r for r in data if not r.get("noise")]
    return [r for r in live if spoke(r)] if human else live


def wilson(hit, total, z=1.96):
    """95% interval on a proportion. A precision of 0.13 over 293 rows and a
    base rate of 0.104 over 747 are not two numbers to compare by eye."""
    if not total:
        return 0.0, 0.0
    share = hit / total
    span = z * math.sqrt(share * (1 - share) / total + z * z / (4 * total * total))
    centre = share + z * z / (2 * total)
    return ((centre - span) / (1 + z * z / total),
            (centre + span) / (1 + z * z / total))


def fisher(a, b, c, d):
    """Two-sided exact test on the 2x2 of fires against pushes.

    Comparing a precision interval with the base rate by eye is not a test:
    the caught pushes sit inside the pushes, so the two proportions are not
    independent samples. The table below asks the question the eyeball was
    reaching for, using the rows the gate did not fire on as well."""
    total = a + b + c + d

    def odds(x):
        return comb(a + b, x) * comb(c + d, a + c - x) / comb(total, a + c)

    seen = odds(a)
    low = max(0, a + c - (c + d))
    high = min(a + b, a + c)
    return sum(odds(x) for x in range(low, high + 1)
               if odds(x) <= seen * (1 + 1e-9))


def association(real, fires):
    caught = sum(1 for r in real if fires(r) and r.get("push"))
    loud = sum(1 for r in real if fires(r) and not r.get("push"))
    missed = sum(1 for r in real if not fires(r) and r.get("push"))
    quiet = sum(1 for r in real if not fires(r) and not r.get("push"))
    return caught, loud, missed, quiet, fisher(caught, loud, missed, quiet)


def score(real, fires):
    fired = [r for r in real if fires(r)]
    caught = [r for r in fired if r.get("push")]
    hits = sum(1 for r in real if r.get("push"))
    prec = len(caught) / max(len(fired), 1)
    rec = len(caught) / max(hits, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return len(fired), prec, rec, f1, wilson(len(caught), len(fired))


def classes(real):
    seen = {}
    for r in real:
        for hit in r.get("firm") or []:
            seen.setdefault(hit.split(":")[0].rstrip(), []).append(r)
    return seen


def firm_of(row, off=()):
    return [h for h in (row.get("firm") or [])
            if h.split(":")[0].rstrip() not in off]


def line(name, got):
    fires, prec, rec, f1, band = got
    print(f"{name:22} {fires:4}  {prec:.3f}  {rec:.3f}  {f1:.3f}"
          f"  [{band[0]:.3f}, {band[1]:.3f}]")


def main():
    named = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = named[0] if named else os.path.join(HERE, "corpus.json")
    real = rows(path, human="--human" in sys.argv)
    hits = sum(1 for r in real if r.get("push"))
    band = wilson(hits, len(real))
    print(f"{len(real)} closings, {hits} pushes, base "
          f"{100.0 * hits / len(real):.1f}% [{100.0 * band[0]:.1f}, {100.0 * band[1]:.1f}]")
    print(f"{'config':22} {'fires':>4}  {'prec':>5}  {'rec':>5}  {'f1':>5}")
    line("always fires", score(real, lambda r: True))
    line("patterns", score(real, lambda r: bool(r.get("firm"))))
    line("patterns+doubt", score(real, lambda r: bool(r.get("hits"))))
    line("judge", score(real, lambda r: r.get("verdict") == "STOP"))
    line("either (shipped)", score(real, lambda r: bool(r.get("firm")) or r.get("verdict") == "STOP"))
    line("both", score(real, lambda r: bool(r.get("firm")) and r.get("verdict") == "STOP"))
    print()
    print(f"{'class':22} {'fires':>4}  {'prec':>5}")
    for name, group in sorted(classes(real).items(),
                              key=lambda kv: -len(kv[1])):
        caught = sum(1 for r in group if r.get("push"))
        edge = wilson(caught, len(group))
        print(f"{name:22} {len(group):4}  {caught / len(group):.3f}"
              f"  [{edge[0]:.3f}, {edge[1]:.3f}]")
    print()
    print(f"{'only this lane fires':22} {'fires':>4}  {'prec':>5}")
    line("firm patterns alone", score(
        real, lambda r: bool(r.get("firm")) and r.get("verdict") != "STOP"))
    line("judge alone", score(
        real, lambda r: not r.get("firm") and r.get("verdict") == "STOP"))
    line("doubt, judge passes", score(
        real, lambda r: bool(r.get("hits")) and not r.get("firm")
        and r.get("verdict") != "STOP"))
    bands = [(0, .5), (.5, .75), (.75, .9), (.9, 1.01)]
    scored = [r for r in real if r.get("sure") is not None
              and r.get("verdict") == "STOP"]
    if scored:
        print()
        print(f"{'judge STOP by certainty':22} {'fires':>4}  {'prec':>5}")
        for low, high in bands:
            part = [r for r in scored if low <= r["sure"] < high]
            if not part:
                continue
            caught = sum(1 for r in part if r.get("push"))
            edge = wilson(caught, len(part))
            print(f"{f'{low:.2f}-{high:.2f}':22} {len(part):4}"
                  f"  {caught / len(part):.3f}  [{edge[0]:.3f}, {edge[1]:.3f}]")
    print()
    cell = association(real, lambda r: bool(r.get("firm")) or r.get("verdict") == "STOP")
    print(f"fires and pushes: {cell[:4]} Fisher p={cell[4]:.4f}")

    print()
    off, best = set(), score(real, lambda r: bool(r.get("firm")) or r.get("verdict") == "STOP")
    while True:
        moved = None
        for name in classes(real):
            if name in off:
                continue
            drop = off | {name}
            got = score(real, lambda r: bool(firm_of(r, drop)) or r.get("verdict") == "STOP")
            if got[1] > best[1]:
                moved, best = name, got
        if not moved:
            break
        off.add(moved)
    print("demoting", sorted(off) or "nothing")
    line("greedy demotion", best)


if __name__ == "__main__":
    main()
