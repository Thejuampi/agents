#!/usr/bin/env python3
"""Concrete next actions, found without asking the model anything.

The proactive question used to hand the agent a checklist and hope: look for
the test you did not write, the doc that is now wrong, the neighbour with the
same bug. Measured over its first blocks, three in five bought no work at all -
the worst conversion of any lane in the gate. A general question is easy to
answer with a general no.

These are found from the turn's own tool calls. Cheap, deterministic, and
specific enough that answering no takes evidence rather than a shrug."""
import os
import re

SOURCE = (".kt", ".java", ".py", ".ts", ".tsx", ".swift", ".go", ".rs", ".cs")
TEST = re.compile(r"(^|/)tests?(/|_)|/spec/|(^|/)test_|(test|spec)s?[.][a-z]+$",
                  re.IGNORECASE)
"""A path that is itself a test. Paths arrive with forward slashes only."""
DOC = (".md", ".rst", ".adoc", ".txt")


SHELL = re.compile(r'(?:^|[>\s"])([\w./:-]+[.](?:kt|java|py|ts|tsx|md|rst|txt|go|rs|cs|swift))')
"""A path a shell command wrote to.

Half the writing in a session never touches the Write tool: it is a heredoc,
a sed, a redirect. This turn wrote four files that way and the proactive
question came back empty, which is how the gap was found."""

WRITERS = ("write", "edit", "multiedit", "notebookedit")
SHELLS = ("bash", "powershell")


def written(entry):
    """Files this assistant message wrote, from the tool calls themselves."""
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return []
    out = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = str(block.get("name") or "").lower()
        payload = block.get("input") or {}
        if name in WRITERS:
            path = payload.get("file_path")
            if isinstance(path, str):
                out.append(path.replace(chr(92), "/"))
        elif name in SHELLS:
            command = payload.get("command")
            if isinstance(command, str):
                out += [m.replace(chr(92), "/")
                        for m in SHELL.findall(command)]
    return out


def found(paths):
    """What the turn changed and did not follow through on."""
    code = [p for p in paths if p.lower().endswith(SOURCE) and not TEST.search(p)]
    tests = [p for p in paths if TEST.search(p)]
    docs = [p for p in paths if p.lower().endswith(DOC)]
    out = []
    if code and not tests:
        out.append("you changed {names} and wrote no test this turn - is the "
                   "case you just fixed covered?".format(
                       names=", ".join(os.path.basename(p) for p in code[:3])))
    if code and not docs:
        out.append("nothing in the docs moved with the code - does any of them "
                   "still describe the old behaviour?")
    return out
