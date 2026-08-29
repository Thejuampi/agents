#!/usr/bin/env python3
"""Work a turn started that reports back on its own.

Shared, because two lanes need the same fact and neither can import the other:
check-stop.py loads check-permission.py, so the detection cannot live in
either one.
"""
import json
import os
import re


def entries(transcript):
    try:
        with open(transcript, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


BACKGROUND = ("agent", "task", "monitor", "croncreate", "schedulewakeup")


NOTIFIED = re.compile(r"<tool-use-id>\s*([^<\s]+)", re.IGNORECASE)


def waiting_on(transcript):
    """True when this turn started work that has not reported back yet.

    The harness re-invokes the session when a background task ends, so an
    agent that says it is waiting is describing the mechanism, not dodging.

    A launch is not enough and a missing tool_result is the wrong signal: a
    backgrounded call answers immediately with its task id, so that absence
    never happens and the first version of this measured zero. The end of the
    work arrives as its own <task-notification>, carrying the tool-use-id of
    the call that started it. Launch opens the wait, that notification closes
    it. Read from the tool calls either way - a promise to wait is cheap, a
    launched task is not."""
    live = {}
    for entry in entries(transcript):
        kind = entry.get("type")
        content = entry.get("message", {}).get("content")
        if kind == "user":
            text = content if isinstance(content, str) else " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ) if isinstance(content, list) else ""
            for done in NOTIFIED.findall(text or ""):
                live.pop(done, None)
            if "<task-notification>" in (text or "").lower():
                continue
            if isinstance(content, str) or (isinstance(content, list) and any(
                    isinstance(x, dict) and x.get("type") != "tool_result"
                    for x in content)):
                live.clear()
            continue
        if kind != "assistant" or not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = str(block.get("name") or "").lower()
            payload = block.get("input") or {}
            if name in BACKGROUND or payload.get("run_in_background") is True:
                live[block.get("id")] = name
    return bool(live)


