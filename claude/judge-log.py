#!/usr/bin/env python3
"""Read the side log the gate keeps for itself.

Every decision writes a line the agent never sees: which lane decided, how
sure the model was, which patterns fired. Two things worth acting on show up
here and nowhere else - a block the model was barely sure of, and a pattern
that fires often while the model disagrees. Both mean a pattern needs work.

  python judge-log.py            what the gate did lately
  python judge-log.py --weak     blocks the model was not sure about
  python judge-log.py --patterns which patterns fire, and how often
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("STOP_LOG") or os.path.join(HERE, "judge-log.jsonl")
SHAKY = 0.75


def rows():
    try:
        with open(LOG, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


def label(row):
    return row.get("verdict") or ("passed" if row.get("passed") else "-")


def recent(entries, count=25):
    for row in entries[-count:]:
        sure = row.get("sure")
        mark = f"{sure:.2f}" if isinstance(sure, (int, float)) and sure else "    "
        print(f"{row.get('at', ''):19} {row.get('lane', ''):8} "
              f"{label(row):7} {mark}  {(row.get('head') or '')[:60]}")


def weak(entries):
    shaky = [r for r in entries
             if r.get("verdict") == "STOP"
             and isinstance(r.get("sure"), (int, float))
             and 0 < r["sure"] < SHAKY]
    print(f"{len(shaky)} blocks the model was under {SHAKY} sure of")
    for row in sorted(shaky, key=lambda r: r.get("sure", 1)):
        print(f"  {row['sure']:.2f}  {(row.get('head') or '')[:70]}")
        if row.get("quote"):
            print(f"        points at: {row['quote'][:70]}")


def named(objection):
    """The pattern labels inside a checker's objection.

    What gets logged is the whole reminder, because that is what the checker
    hands back. check-permission lists its labels on a "Matched:" line; every
    other checker has one shape and its title is the name."""
    for line in objection.splitlines():
        if line.startswith("Matched: "):
            names = []
            for part in line[len("Matched: "):].split(","):
                head = part.split(":")[0].strip() if ":" in part else ""
                if head and " " not in head:
                    names.append(head)
            return names
    head = objection.splitlines()[0] if objection.strip() else ""
    return [head.replace("KEEP GOING - ", "").replace("ALMOST - ", "").strip()]


def patterns(entries):
    fired = collections.Counter()
    doubted = collections.Counter()
    for row in entries:
        for hit in row.get("firm") or []:
            fired.update(named(hit))
        for hit in row.get("weak") or []:
            doubted.update(named(hit))
    print(f"{sum(fired.values())} firm hits, {sum(doubted.values())} doubts")
    for name, count in fired.most_common(15):
        print(f"  firm  {count:4}  {name}")
    for name, count in doubted.most_common(15):
        print(f"  weak  {count:4}  {name}")


def main():
    entries = list(rows())
    if not entries:
        print(f"nothing logged yet at {LOG}")
        return 0
    flag = sys.argv[1] if len(sys.argv) > 1 else ""
    lanes = collections.Counter(r.get("lane") for r in entries)
    print(f"{len(entries)} decisions: " +
          ", ".join(f"{n} {k}" for k, n in lanes.most_common()))
    if flag == "--weak":
        weak(entries)
    elif flag == "--patterns":
        patterns(entries)
    else:
        recent(entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
