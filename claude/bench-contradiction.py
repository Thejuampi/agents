#!/usr/bin/env python3
"""Claims the session record contradicts.

Every other measurement in this work is scored against one weak label: whether
the developer pushed back. That label answers "did the human have to ask", and
a false claim only appears in it when the human noticed. A contradiction needs
no label. The agent wrote that it committed; the turn either ran a commit or it
did not, and both halves are in the transcript.
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
claims = mod.load("claims.py")


def commands_of(entry):
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return []
    out = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            command = (block.get("input") or {}).get("command")
            if isinstance(command, str):
                out.append(command)
    return out


def turns(path):
    """Every closing in one transcript with what the turn ran to earn it."""
    out, closing, commands, sofar = [], "", [], []
    for entry in corpus.entries(path):
        if reader.spoke(entry):
            if closing:
                out.append((closing, commands, list(sofar)))
            closing, commands = "", []
            continue
        if entry.get("type") != "assistant":
            continue
        commands += commands_of(entry)
        sofar += commands_of(entry)
        body = corpus.text_of(entry)
        if body:
            closing = body
    if closing:
        out.append((closing, commands, list(sofar)))
    return out


def files():
    rows = json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))
    return sorted({row["file"] for row in rows})


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    said = {"commit": 0, "green": 0}
    broke = {"commit": [], "green": []}
    turn_only = {"commit": 0, "green": 0}
    total = 0
    for path in files():
        for closing, commands, sofar in turns(path):
            total += 1
            body = claimer.unquoted(closing)
            for name in claims.claimed(body):
                said[name] += 1
            for name in claims.contradicted(body, commands):
                turn_only[name] += 1
            for name in claims.contradicted(body, sofar):
                broke[name].append(" ".join(closing.split())[:110])
    print(f"{total} closings")
    for name in said:
        n = len(broke[name])
        print(f"  says {name:6}: {said[name]:4}   nothing in the whole "
              f"session: {n:4} ({100.0 * n / max(said[name], 1):.1f}% of the "
              f"claims)   nothing in this turn: {turn_only[name]}")
    for name in broke:
        print(chr(10) + f"contradicted {name} claims, first 6:")
        for line in broke[name][:6]:
            print("   " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
