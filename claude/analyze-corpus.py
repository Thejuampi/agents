#!/usr/bin/env python3
"""Reads corpus.json and prints every number the paper reports.

The interesting comparison is not blocked closings against unblocked ones:
the gate chooses what it blocks, so that difference is the gate's taste and
nothing else. It is the same trigger on both sides of the install date. Every
closing the gate would fire on is a predicted positive; before 2026-08-28 it
got no block because the gate was not installed, and after it did. The trigger
is held constant and only the treatment moves."""
import json
import os
import sys

NL = chr(10)

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus.json")
INSTALL = "2026-08-28"


DAYS = {}


def day(row):
    """The date the session opened, read from its first stamped entry.

    A session is short next to the gap between eras, so the file's own first
    timestamp places every closing in it."""
    path = row.get("file") or ""
    if path in DAYS:
        return DAYS[path]
    found = ""
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                stamp = json.loads(line).get("timestamp")
                if stamp:
                    found = str(stamp)[:10]
                    break
    except (OSError, ValueError, AttributeError):
        found = ""
    DAYS[path] = found
    return found


def rate(rows):
    hit = sum(1 for r in rows if r.get("push"))
    return hit, len(rows), 100.0 * hit / max(len(rows), 1)


def show(name, rows):
    hit, total, pct = rate(rows)
    print(f"  {name:<34} {hit:>4} of {total:>4}  {pct:5.1f}%")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = json.load(open(CORPUS, encoding="utf-8"))
    real = [r for r in rows if not r.get("noise") and r.get("push") is not None]
    print(f"{len(rows)} closings, {len(real)} labelled")

    print(NL + "Base rate")
    show("every closing", real)

    fired = [r for r in real if r.get("fired")]
    caught = [r for r in fired if r.get("push")]
    pushes = [r for r in real if r.get("push")]
    print(NL + "Gate")
    print(f"  fires {len(fired)} of {len(real)}  prec {len(caught) / max(len(fired), 1):.3f}  rec {len(caught) / max(len(pushes), 1):.3f}")

    print(NL + "Por clase")
    seen = {}
    for row in real:
        for hit in row.get("hits") or []:
            name = hit.split(":")[0].strip()
            seen.setdefault(name, []).append(row)
    for name, group in sorted(seen.items(), key=lambda kv: -len(kv[1]))[:12]:
        show(name, group)

    print(NL + "El mismo disparo, a los dos lados de la instalacion")
    before = [r for r in fired if day(r) < INSTALL]
    after = [r for r in fired if day(r) >= INSTALL]
    show("would fire, gate not installed", before)
    show("would fire, gate installed", after)
    quiet = [r for r in real if not r.get("fired")]
    show("gate stays quiet, before", [r for r in quiet if day(r) < INSTALL])
    show("gate stays quiet, after", [r for r in quiet if day(r) >= INSTALL])

    print(NL + "Bloqueos que el agente realmente recibio")
    for n in (0, 1, 2):
        group = [r for r in real if (r.get("blocks") or 0) == n]
        if group:
            show(f"{n} blocks", group)
    many = [r for r in real if (r.get("blocks") or 0) >= 3]
    if many:
        show("3 or more", many)


if __name__ == "__main__":
    main()
