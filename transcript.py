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
import re


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


IMAGE = re.compile(r"\A\s*\[Image[^\]]*\]\s*")
HARNESS = re.compile(
    r"Request interrupted|This session is being continued|"
    r"Usage limit approaching|no visible output|API Error|"
    r"^Caveat:|^Stop hook feedback", re.IGNORECASE)
"""What the harness says in the developer's place.

A screenshot arrives as a placeholder carrying its pixel size, an escape
arrives as an interrupt notice, a compaction arrives as a paragraph about
itself. Read as a reply, the push judge scores boilerplate: 152 of 753 rows
in the first build had no developer words in them at all."""


def reply_of(text):
    """The developer's own words, or None when there are none."""
    body = " ".join(str(text or "").split())
    while True:
        stripped = IMAGE.sub("", body, count=1)
        if stripped == body:
            break
        body = stripped
    if not body or HARNESS.search(body[:120]):
        return None
    return body

