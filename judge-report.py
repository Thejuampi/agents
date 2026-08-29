#!/usr/bin/env python3
"""Grades every block the gate made, by reading what the agent did next.

The log says what the gate decided. It cannot say whether the decision was
right. That answer is already written a few lines further down the same
transcript: a block wakes the agent, and either the agent goes and works or
it writes another paragraph and stops again. Tool calls after a block are
the label, and nobody has to hand it over.

A block that bought work is a block worth keeping. A block that bought
another paragraph is a pattern to demote or a prompt to fix. Run it whenever
you want the current numbers; the cron runs it on its own and pings Rick."""
import glob
import importlib.util
import json
import os
import sys
import time

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

HERE = os.path.dirname(os.path.abspath(__file__))

reader = mod.load("transcript.py")
LOG = os.environ.get("STOP_LOG") or os.path.join(HERE, "judge-log.jsonl")
PROJECTS = os.path.expanduser("~/.claude/projects")
WORKED = 3
ENOUGH = 8
MOSTLY = 0.7


def decisions():
    try:
        handle = open(LOG, encoding="utf-8")
    except OSError:
        return
    with handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                yield entry


def turns(path):
    try:
        handle = open(path, encoding="utf-8")
    except OSError:
        return []
    rows = []
    with handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                rows.append(entry)
    return rows


spoke = reader.spoke


def texts(entry):
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return ""
    return " ".join(b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text").strip()


def after(rows, head):
    """Tool calls between the blocked message and the next time the user spoke.

    Returns None when the message cannot be found, which happens for a
    session still running or a transcript the harness has since rewritten."""
    start = -1
    for i, entry in enumerate(rows):
        if entry.get("type") == "assistant" and texts(entry)[:len(head)] == head:
            start = i
    if start < 0:
        return None
    count = 0
    for entry in rows[start + 1:]:
        if spoke(entry):
            break
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, list):
            count += sum(1 for b in content
                         if isinstance(b, dict) and b.get("type") == "tool_use")
    return count


def locate(entry):
    """The transcript a decision was made on.

    Entries written before the log carried a path only kept the first twelve
    characters of the session id, which is still enough to find the file."""
    path = entry.get("file")
    if path and os.path.exists(path):
        return path
    stem = entry.get("session") or ""
    if len(stem) < 8:
        return ""
    for found in glob.glob(os.path.join(PROJECTS, "*", stem + "*.jsonl")):
        return found
    return ""


PATTERNS = os.path.join(HERE, "stop-patterns.txt")
SHAPES = ("shape", "judge", "waiting", "proactive")


def labels():
    """The class names that exist, so a block cannot invent one.

    A reminder quotes the repository files it wants read, and those names sit
    on the same line as the match. Read loosely they became classes of their
    own, and the report advised demoting README.md."""
    found = set(SHAPES)
    try:
        handle = open(PATTERNS, encoding="utf-8")
    except OSError:
        return found
    with handle:
        for raw in handle:
            line = raw.strip().lstrip("-").strip()
            if line and not line.startswith("#") and ":" in line:
                found.add(line.split(":")[0].strip())
    return found


def classes(entry):
    if entry.get("ask"):
        return ["proactive"]
    if entry.get("waiting"):
        return ["waiting"]

    known = labels()
    names = []
    for text in (entry.get("firm") or []) + (entry.get("weak") or []):
        for part in text.split("Matched: ")[-1].split(chr(10))[0].split(","):
            head = part.strip().split(":")[0].strip()
            if head in known or head.rstrip("?") in known:
                names.append(head)
    return names or ["judge"]


def graded():
    rows = []
    for entry in decisions():
        if entry.get("passed") or (entry.get("verdict") in ("skip", "OK")
                                   and not entry.get("ask")):
            continue
        path = locate(entry)
        if not path:
            continue
        did = after(turns(path), (entry.get("head") or "")[:80])
        if did is None:
            continue
        rows.append((entry, did))
    return rows


def table(title, groups):
    out = [title]
    for name in sorted(groups, key=lambda n: -len(groups[n])):
        did = groups[name]
        wasted = [d for d in did if d < WORKED]
        share = 100.0 * len(wasted) / len(did)
        out.append(f"  {name:<22} {len(did):>4} blocks  {share:>5.0f}% bought nothing")
    return out


def ripe_ones(by_class):
    return [(n, v) for n, v in by_class.items()
            if len(v) >= ENOUGH and len([d for d in v if d < WORKED]) / len(v) >= MOSTLY]


def brief():
    """What the gate has learned since the last time anyone looked.

    Wired to session start, so it speaks into Rick's context on its own. A
    report nobody reads tunes nothing, and a report that speaks every time
    gets skipped, so it stays quiet unless a pattern is ripe and it says so
    at most once a day."""
    rows = graded()
    by_class = {}
    for entry, did in rows:
        for name in classes(entry):
            by_class.setdefault(name, []).append(did)
    ripe = ripe_ones(by_class)
    if not ripe:
        return 0
    stamp = LOG + ".stamp"
    today = time.strftime("%Y-%m-%d")
    try:
        if open(stamp, encoding="utf-8").read().strip() == today:
            return 0
    except OSError:
        pass
    try:
        open(stamp, "w", encoding="utf-8").write(today)
    except OSError:
        pass
    names = ", ".join(n for n, _ in ripe)
    print(f"El guardia junto evidencia contra estos patrones: {names}. "
          f"Corre judge-report.py, pasalos a duda en stop-patterns.txt, "
          f"corre la suite y commitea.")
    return 0


def main():
    if "--brief" in sys.argv:
        return brief()
    rows = graded()
    if not rows:
        print("no graded blocks yet")
        return 0
    wasted = [r for r in rows if r[1] < WORKED]
    out = [f"{len(rows)} blocks graded, {len(wasted)} bought nothing "
           f"({100.0 * len(wasted) / len(rows):.0f}%)", ""]

    by_class = {}
    for entry, did in rows:
        for name in classes(entry):
            by_class.setdefault(name, []).append(did)
    out += table("Por patron", {k: v for k, v in by_class.items() if len(v) >= 3})

    bands = {}
    for entry, did in rows:
        sure = entry.get("sure")
        if sure is None:
            continue
        for lo, hi, name in ((0, .5, "0.00-0.50"), (.5, .75, "0.50-0.75"),
                             (.75, .9, "0.75-0.90"), (.9, 1.01, "0.90-1.00")):
            if lo <= sure < hi:
                bands.setdefault(name, []).append(did)
    if bands:
        out += [""] + table("Por certeza del juez", bands)

    ripe = ripe_ones(by_class)
    if ripe:
        out += ["", "Ya hay evidencia para demoter:"]
        for name, did in sorted(ripe, key=lambda r: -len(r[1])):
            out.append(f"  {name} - {len(did)} bloqueos y casi ninguno compro trabajo. "
                       "Pasalo a duda en stop-patterns.txt.")

    if wasted:
        out += ["", "Los ultimos que no compraron nada:"]
        for entry, did in wasted[-6:]:
            out.append(f"  {entry.get('at', '')} {did} tools | "
                       f"{' '.join((entry.get('head') or '').split())[:70]}")
    print(chr(10).join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
