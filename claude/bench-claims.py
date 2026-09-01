#!/usr/bin/env python3
"""Does checking a claim against evidence beat guessing at intent?

The judge reads a closing and asks whether it sounds finished. Precision is
0.119 against a base rate of 0.104, which is nearly no information at all. A
claim is different in kind: "the suite is green" is either backed by a command
this turn ran or it is not, and that question has an answer in the transcript
rather than an opinion about it.

This scores that lane on the same labelled rows, with no model in the loop.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

KEPT = list(sys.argv)
sys.argv = [sys.argv[0]]
corpus = mod.load("corpus.py")
claimer = mod.load("check-done-claim.py")
sys.argv = KEPT

reader = mod.load("transcript.py")
claim = mod.load("claim.py")


def key(path, closing):
    return path, " ".join(closing.split())[:120]


def labels():
    rows = json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))
    return {key(r["file"], r["closing"]): r for r in rows
            if not r.get("noise") and r.get("push") is not None}


def ran(commands):
    """Did any command in this turn exercise the product?"""
    root = HERE.replace(chr(92), "/").lower()
    for command in commands:
        for head in claimer.steps(command):
            if claimer.exercised(head, root) or claimer.live(head):
                return True
    return False


def turns(path):
    """Every closing in one transcript with what the turn ran to earn it."""
    out, closing, commands = [], "", []
    for entry in corpus.entries(path):
        if reader.spoke(entry):
            if closing:
                out.append((closing, commands))
            closing, commands = "", []
            continue
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                command = (block.get("input") or {}).get("command")
                if isinstance(command, str):
                    commands.append(command)
        body = corpus.text_of(entry)
        if body:
            closing = body
    if closing:
        out.append((closing, commands))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    known = labels()
    groups = {"claim, nothing run": [], "claim, product exercised": [],
              "no claim": []}
    for path in sorted({k[0] for k in known}):
        for closing, commands in turns(path):
            row = known.get(key(path, closing))
            if row is None:
                continue
            if claim.CLAIM.search(claimer.unquoted(closing)):
                name = ("claim, product exercised" if ran(commands)
                        else "claim, nothing run")
            else:
                name = "no claim"
            groups[name].append(bool(row["push"]))

    every = [p for rows in groups.values() for p in rows]
    print(f"{len(every)} closings matched, base rate "
          f"{100.0 * sum(every) / max(len(every), 1):.1f}%")
    for name, rows in groups.items():
        if not rows:
            continue
        print(f"  {name:26} {sum(rows):3} of {len(rows):4}  "
              f"{100.0 * sum(rows) / len(rows):5.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
