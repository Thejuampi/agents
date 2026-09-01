#!/usr/bin/env python3
"""Reads a transcript and reports the stops check-permission.py would miss.

Every assistant turn that ends the model's output is a stop. The hook should
have fired on the ones that handed work back. This prints the ones it misses,
so the pattern list grows from real transcripts instead of from guesses.

Usage: scan-stops.py <transcript.jsonl> [--since 2026-08-28T02:56] [--all]
"""
import importlib.util
import json
import os
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
hook = mod.load("check-permission.py")

claim = mod.load("check-done-claim.py")


def turns(path):
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            kind = entry.get("type")
            if kind not in ("assistant", "user"):
                continue
            content = entry.get("message", {}).get("content")
            if isinstance(content, list):
                text = " ".join(b.get("text", "") for b in content
                                if isinstance(b, dict) and b.get("type") == "text").strip()
                tools = any(isinstance(b, dict) and b.get("type") == "tool_use" for b in content)
            else:
                text, tools = (content or "").strip(), False
            out.append({"kind": kind, "text": text, "tools": tools,
                        "at": entry.get("timestamp", "")[:19]})
    return out


def closing_messages(rows):
    """An assistant text with no tool call, followed by a user turn: a stop."""
    stops = []
    acted = False
    for i, row in enumerate(rows):
        if row["kind"] == "user":
            acted = False
        if row["tools"]:
            acted = True
        if row["kind"] != "assistant" or not row["text"] or row["tools"]:
            continue
        row["acted"] = acted
        nxt = next((r for r in rows[i + 1:] if r["kind"] in ("assistant", "user")), None)
        if nxt is None or nxt["kind"] == "user":
            stops.append(row)
    return stops


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    since = ""
    if "--since" in sys.argv:
        since = sys.argv[sys.argv.index("--since") + 1]
    show_all = "--all" in sys.argv

    rows = [r for r in turns(path) if r["at"] >= since]
    stops = closing_messages(rows)
    missed = []
    caught = 0
    for stop in stops:
        if "BLOCKED:" in stop["text"]:
            continue
        if (hook.offenders(stop["text"], None, stop.get("acted", True))
                or claim.CLAIM.search(claim.unquoted(stop["text"]))):
            caught += 1
        else:
            missed.append(stop)

    print(f"{len(stops)} stops, {caught} caught, {len(missed)} uncaught")
    for stop in (missed if show_all else missed[-12:]):
        tail = stop["text"][-400:].replace("\n", " ")
        print(f"\n--- {stop['at']}\n{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
