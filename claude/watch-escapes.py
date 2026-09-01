#!/usr/bin/env python3
"""Hunt a session for closings that got out and should not have.

The hook only ever sees one message at a time. This reads a whole transcript
the way a reviewer would: every closing, what the patterns said about it, and
- for the ones the patterns let through - what the local model says. A clean
message the model calls STOP is an escape, and it is the only kind worth
reading, because the blocked ones already got their answer.

It also counts the BLOCKED: claims, which is the other way out. One that never
carried a release phrase never got read, so it was a try, not a passage.

    python watch-escapes.py <transcript.jsonl> [--since N]
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(HERE, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perm = load("check-permission.py", "perm")
judge = load("llm_judge.py", "judge")
release = load("release.py", "release")


def turns(path):
    """Closing messages with the user message that preceded them."""
    out, last, asked, pending = [], None, None, None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            content = entry.get("message", {}).get("content")
            if entry.get("type") == "user":
                text = content if isinstance(content, str) else " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text") \
                    if isinstance(content, list) else ""
                if text.strip():
                    if last:
                        out.append((pending, last))
                    pending, last = text.strip(), None
                continue
            if entry.get("type") != "assistant" or not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text" \
                        and block.get("text", "").strip():
                    last = block["text"]
    if last:
        out.append((pending, last))
    return out


def say(text):
    sys.stdout.buffer.write(text.encode("utf-8", "replace") + bytes([10]))


def main():
    if len(sys.argv) < 2:
        say(__doc__.strip().splitlines()[-1].strip())
        return 2
    path = sys.argv[1]
    since = 0
    if "--since" in sys.argv:
        since = int(sys.argv[sys.argv.index("--since") + 1])

    rows = turns(path)[since:]
    clean = held = firm = 0
    escapes, claims = [], []
    for number, (asked, text) in enumerate(rows, since + 1):
        if release.claims_block(text):
            claims.append((number, text))
        hits = perm.offenders(text)
        if not hits:
            clean += 1
            verdict, _ = judge.stop_verdict(text, asked=asked or "")
            if verdict == "STOP":
                escapes.append((number, text))
        elif all(perm.weak(h.split(":")[0]) for h in hits):
            held += 1
        else:
            firm += 1

    say(f"{len(rows)} closings read from turn {since + 1}")
    say(f"  {firm} stopped by a pattern")
    say(f"  {held} sent to the model by a weak pattern")
    say(f"  {clean} passed the patterns clean")
    say(f"  {len(escapes)} of those the model calls a stop  <- escapes")
    if claims:
        say(f"  {len(claims)} BLOCKED: claims")
    for number, text in escapes:
        say("")
        say(f"--- turn {number}")
        say("    " + text.strip()[-300:].replace(chr(10), " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
