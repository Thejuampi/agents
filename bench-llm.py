#!/usr/bin/env python3
"""Measures a local model as a stop detector against the real transcripts.

Three sets, in order of how much the answer is trusted:
  gold  - the message right before Juan pushed back. He objected, so it is a
          stop. Anything missed here is a real miss.
  known - what the pattern list already catches. Agreement here is cheap.
  quiet - closing messages the patterns miss and Juan never objected to. A
          STOP here is a candidate the patterns do not know yet, to read by eye.

Usage: bench-llm.py [model] [--limit N]
"""
import glob
import importlib.util
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(os.path.dirname(HERE), "projects")
TRANSCRIPTS = os.environ.get("BENCH_TRANSCRIPTS") or os.path.join(
    PROJECTS, "*", "*.jsonl")


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(HERE, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan = load("scan-stops.py", "scan")
audit = load("audit-interventions.py", "audit")
judge = load("llm_judge.py", "judge")
perm, claim = scan.hook, scan.claim


def caught_by_patterns(text, acted):
    return bool(perm.offenders(text, None, acted)) or bool(
        claim.CLAIM.search(claim.unquoted(text)))


def collect():
    gold, known, quiet = [], [], []
    for path in glob.glob(TRANSCRIPTS):
        rows = audit.rows(path)
        pushed = set()
        last = None
        for row in rows:
            if row["kind"] == "assistant" and row["text"]:
                last = row["text"]
                continue
            if row["kind"] != "user" or row["result"] or not row["text"]:
                continue
            if "STOP HOOK" in row["text"] or audit.SYNTHETIC.search(row["text"][:600]):
                last = None
                continue
            if audit.PUSHBACK.search(row["text"]) and last:
                pushed.add(last)
        for stop in scan.closing_messages(scan.turns(path)):
            text = stop["text"]
            if "BLOCKED:" in text:
                continue
            if text in pushed:
                gold.append(text)
            elif caught_by_patterns(text, stop.get("acted", True)):
                known.append(text)
            else:
                quiet.append(text)
    return gold, known, quiet


def score(name, items, want, limit):
    hit = 0
    times = []
    disagreed = []
    for text in items[:limit]:
        label, seconds = judge.verdict(text)
        times.append(seconds)
        if label == want:
            hit += 1
        else:
            disagreed.append((label, text))
    total = len(items[:limit])
    median = sorted(times)[len(times) // 2] if times else 0
    print(f"{name}: {hit}/{total} said {want}   median {median:.2f}s")
    return disagreed


def main():
    model = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    if model:
        judge.MODEL = model
    limit = 40
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    gold, known, quiet = collect()
    print(f"model {judge.MODEL}   gold {len(gold)}  known {len(known)}  quiet {len(quiet)}\n")

    started = time.time()
    missed = score("gold ", gold, "STOP", limit)
    score("known", known, "STOP", limit)
    flagged = score("quiet", quiet, "STOP", limit)
    print(f"\nwall {time.time() - started:.1f}s")

    for label, text in missed:
        print(f"\n--- GOLD MISSED (said {label})\n{text[-260:]}".replace("\n", " "))
    for label, text in flagged[:8]:
        if label == "STOP":
            print(f"\n--- QUIET FLAGGED\n{text[-260:]}".replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
