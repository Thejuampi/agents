#!/usr/bin/env python3
"""Is the conversion rate an artifact of where we put the threshold?

A block bought work when the agent made three tool calls before the developer
spoke again, and three is a number we chose. If the answer moves with it, the
result is about the threshold. This prints the rate across a range of cuts and
the median block beside them, so a reader can see how far the data sits from
the line."""
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CUTS = (1, 2, 3, 4, 5, 8)


def load(alias, filename):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wilson(hit, total, z=1.96):
    if not total:
        return 0.0, 0.0
    share = hit / total
    span = z * math.sqrt(share * (1 - share) / total + z * z / (4 * total * total))
    centre = share + z * z / (2 * total)
    return ((centre - span) / (1 + z * z / total),
            (centre + span) / (1 + z * z / total))


def main():
    report = load("report", "judge-report.py")
    did = [calls for _, calls in report.graded()]
    if not did:
        print("no graded blocks in the log")
        return 1
    order = sorted(did)
    print(f"{len(did)} graded blocks, median {order[len(order) // 2]} tool calls,"
          f" {sum(1 for d in did if not d)} bought nothing at all")
    print(f"{'threshold':10} {'bought':>6} {'rate':>6}  95% CI")
    for cut in CUTS:
        hit = sum(1 for d in did if d >= cut)
        band = wilson(hit, len(did))
        print(f"{cut:<10} {hit:>6} {hit / len(did):>6.3f}"
              f"  [{band[0]:.3f}, {band[1]:.3f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
