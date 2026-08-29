#!/usr/bin/env python3
"""What counts as the developer speaking, in one place.

The gate wakes the agent by writing to stderr, and the harness feeds that back
as a plain user string. Every reader of a transcript has to know it is not a
person, and each one that forgot broke differently:

  background.py cleared its launched-work state on the wake, so the waiting
  reminder stopped applying right after the first block.

  judge-report.py closed its counting window there, so every block graded as
  zero tool calls bought.

  the corpus handed the reminder to the push judge as if a person wrote it."""

WAKE = "Stop hook feedback:"


def spoke(entry):
    """A real developer turn. Not a tool result, not this gate's own wake."""
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return WAKE not in content[:200]
    if not isinstance(content, list):
        return False
    if any(isinstance(b, dict) and b.get("type") == "text"
           and WAKE in str(b.get("text") or "")[:200] for b in content):
        return False
    return any(isinstance(b, dict) and b.get("type") != "tool_result"
               for b in content)
