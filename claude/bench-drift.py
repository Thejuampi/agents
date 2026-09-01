#!/usr/bin/env python3
"""Is the failure rate a constant, or did the developer change over the month?

Every rate in this work is quoted against one base rate, which assumes the
thing being measured holds still for 26 days. It does not have to. A developer
who learns what the gate catches writes different closings, and a corpus that
spans a habit change carries two populations under one number. This reads the
session start time out of each transcript and splits the push label by week."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def started(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                stamp = json.loads(line).get("timestamp")
            except ValueError:
                continue
            if stamp:
                return stamp[:10]
    return None


def wilson(hit, total, z=1.96):
    if not total:
        return 0.0, 0.0
    share = hit / total
    span = z * math.sqrt(share * (1 - share) / total + z * z / (4 * total * total))
    centre = share + z * z / (2 * total)
    return ((centre - span) / (1 + z * z / total),
            (centre + span) / (1 + z * z / total))


def mantel(strata):
    """Cochran-Mantel-Haenszel across weeks.

    The base rate moves, so a single 2x2 over the whole corpus mixes weeks
    that differ in what it is measuring. This asks the same question inside
    each week and pools the answers, which is the test the pooled one should
    have been."""
    top = 0.0
    bottom = 0.0
    for a, b, c, d in strata:
        total = a + b + c + d
        if total < 2:
            continue
        top += a - (a + b) * (a + c) / total
        bottom += ((a + b) * (c + d) * (a + c) * (b + d)
                   / (total * total * (total - 1)))
    if not bottom:
        return 0.0, 1.0
    chi = (abs(top) - 0.5) ** 2 / bottom
    return chi, math.erfc(math.sqrt(chi / 2))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "corpus.json")
    rows = [r for r in json.load(open(path, encoding="utf-8"))
            if not r.get("noise")]
    dated = {}
    for row in rows:
        day = started(row.get("file") or "")
        if day:
            dated.setdefault(day, []).append(row)
    if not dated:
        print("no transcript carries a timestamp")
        return 1
    weeks = {}
    for day, group in dated.items():
        key = day[:8] + ("01" if day[8:] < "08" else
                         "08" if day[8:] < "15" else
                         "15" if day[8:] < "22" else "22")
        weeks.setdefault(key, []).extend(group)
    print(f"{'week of':12} {'closings':>8} {'pushes':>7} {'rate':>6}  95% CI")
    for key in sorted(weeks):
        group = weeks[key]
        hit = sum(1 for r in group if r.get("push"))
        band = wilson(hit, len(group))
        print(f"{key:12} {len(group):>8} {hit:>7} {hit / len(group):>6.3f}"
              f"  [{band[0]:.3f}, {band[1]:.3f}]")
    print()
    print(f"{'week of':12} {'fires':>8} {'caught':>7} {'prec':>6}  95% CI")
    for key in sorted(weeks):
        fired = [r for r in weeks[key]
                 if r.get("firm") or r.get("verdict") == "STOP"]
        if not fired:
            continue
        caught = sum(1 for r in fired if r.get("push"))
        band = wilson(caught, len(fired))
        print(f"{key:12} {len(fired):>8} {caught:>7} {caught / len(fired):>6.3f}"
              f"  [{band[0]:.3f}, {band[1]:.3f}]")
    strata = []
    for key in sorted(weeks):
        group = weeks[key]
        loud = [r for r in group if r.get("firm") or r.get("verdict") == "STOP"]
        quiet = [r for r in group if r not in loud]
        strata.append((sum(1 for r in loud if r.get("push")),
                       sum(1 for r in loud if not r.get("push")),
                       sum(1 for r in quiet if r.get("push")),
                       sum(1 for r in quiet if not r.get("push"))))
    chi, odds = mantel(strata)
    print()
    print(f"stratified by week: chi2 {chi:.3f}, p {odds:.5f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
