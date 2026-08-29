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



def said_by(entry):
    """The text of one entry, developer or agent, with nothing else in it."""
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return " ".join(b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text")


def exchanges(entries, turns=4):
    """The last few things the developer asked, each with the agent's answer.

    One message is not always enough to judge a reply against. A developer who
    asks for a measurement, reads it, and then says "y ahora el resto" has left
    the subject in the turn before; a closing that names the next step reads
    like an offer against the last message alone and like a plan already agreed
    against the two before it.

    The answer to a request is the last thing the agent said before the
    developer spoke again. Everything between is working: tool calls, and the
    paragraphs the gate itself woke the agent to write. Neither is a reply."""
    pairs = []
    for entry in entries:
        if spoke(entry):
            words = reply_of(said_by(entry))
            if words:
                pairs.append([words, ""])
            continue
        if entry.get("type") != "assistant" or not pairs:
            continue
        words = " ".join(said_by(entry).split())
        if words:
            pairs[-1][1] = words
    return [(ask, answer) for ask, answer in pairs[-turns:]]
