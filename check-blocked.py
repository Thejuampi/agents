#!/usr/bin/env python3
"""Stop hook. Every other checker lets a message through the moment it says
BLOCKED:. That escape exists for the real thing - no device, no credential, no
network - and it is the cheapest evasion in the system, because nothing has
ever asked whether the blocker is real.

This asks. A blocker earned by trying and failing passes. A blocker declared
from an armchair does not.

Three questions, all answerable from the transcript:
  - did anything run this turn? You cannot be blocked by what you never tried.
  - is it one thing? A list of open items is a status report wearing a hat.
  - how many turns in a row has this session been blocked? A blocker that
    survives three closings without a single tool call is a habit.
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location(
    "perm", os.path.join(HERE, "check-permission.py"))
perm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perm)

MARK = re.compile(r"BLOCKED:", re.IGNORECASE)
STREAK = 3

REMINDER = """STOP HOOK - THE BLOCKER DOES NOT HOLD UP

You wrote BLOCKED: and that ends the turn. It has to be earned:

{gaps}

The escape is for the thing you cannot do here - no device, no credential, no
network - after you tried. It is not a way to end a turn.

Take the blocker back to the point where something actually failed. If it does
fail, say the one thing you need and what you ran to find that out."""


def claims(path):
    """Every closing message this session made, in order, and whether each one
    declared a blocker. A single one is a fact; a run of them is a posture."""
    out = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "assistant":
                    continue
                content = entry.get("message", {}).get("content")
                if not isinstance(content, list):
                    continue
                text = " ".join(b.get("text", "") for b in content
                                if isinstance(b, dict) and b.get("type") == "text").strip()
                if text:
                    out.append(bool(MARK.search(perm.unquoted(text))))
    except OSError:
        return []
    return out


def demand(message):
    """What the message asks for, from BLOCKED: to the end of its paragraph."""
    match = MARK.search(message)
    if not match:
        return ""
    rest = message[match.end():]
    return rest.split("\n\n")[0].strip()


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("stop_hook_active"):
        return 0

    transcript = payload.get("transcript_path") or ""
    raw = perm.last_assistant_text(transcript)
    message = perm.unquoted(raw or "")
    if not raw or not MARK.search(message):
        return 0

    gaps = []
    if not perm.acted_this_turn(transcript):
        gaps.append("  - nothing ran this turn. A blocker you did not walk into "
                    "is a guess.")

    asked = demand(message)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", asked) if s.strip()]
    if len(sentences) > 2 or asked.count("\n") >= 2:
        gaps.append("  - it names more than one thing. One blocker, one need, "
                    "one sentence. The rest is work you can still do.")

    history = claims(transcript)
    streak = 0
    for blocked in reversed(history):
        if not blocked:
            break
        streak += 1
    if streak >= STREAK:
        gaps.append(f"  - {streak} closings in a row declared a blocker. "
                    "Whatever is left, the way out is a tool call.")

    if not gaps:
        return 0

    sys.stderr.write(REMINDER.format(gaps="\n".join(gaps)) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
