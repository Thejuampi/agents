#!/usr/bin/env python3
"""A requirement is closed only after the docs and the review.

Both were skipped on a real slice, and the reason was written down: the
project's own process file called BMAD a menu and the review optional. The
file says the opposite now, and a rule that only lives in a file depends on
somebody reading it. This is the same rule, wired.

It arms itself off the repo. A tree whose AGENTS.md or process file states
the PRD -> spec -> build -> review cycle is a tree where the cycle applies;
anywhere else this checker stands down and costs nothing.
"""
import importlib.util
import json
import os
import re
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

HERE = os.path.dirname(os.path.abspath(__file__))
MAYBE = 3


def _load(name, filename):
    return mod.load(filename)


perm = _load("perm", "check-permission.py")
dead = _load("dead", "check-dead-code.py")
claim = _load("claim", "check-done-claim.py")
host = _load("host", "host.py")

RULES = ("AGENTS.md", "CLAUDE.md", ".grok/rules/bmad.md")

CYCLE = re.compile(
    r"prd\s*(->|→|>)\s*spec\s*(->|→|>)\s*build\s*(->|→|>)\s*review",
    re.IGNORECASE)

DOC = (".md", ".mdx", ".rst", ".adoc")

REVIEWED = re.compile(
    r"bmad[- ]?(code[- ])?review|/code-review|ultrareview|"
    r"subagent_type[\"'\s:=]+(reviewer|advisor|qa)",
    re.IGNORECASE)

REMINDER = """ALMOST - THE CYCLE IS NOT CLOSED YET

{items}

The build is the hard part and it is done. This repo runs requirements as PRD -> spec -> build -> review, and the last steps are the ones that make the work survive somebody else reading it. Update what the change made untrue, run the review, then close."""


def cycle_repo(cwd):
    """True when this tree says requirements run the cycle.

    Read from the repo, not from a setting. The rule belongs to the project
    that wrote it down, and a tree that never adopted it must not pay for it."""
    for name in RULES:
        path = os.path.join(cwd, name)
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                if CYCLE.search(handle.read()):
                    return True
        except OSError:
            continue
    return False


def reviewed(transcript):
    """A review is a thing that ran, so it is looked for in the tool calls."""
    for entry in host.entries(transcript):
        content = entry.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and REVIEWED.search(
                    json.dumps(block.get("input") or {})):
                return True
            if block.get("type") == "tool_use" and REVIEWED.search(
                    str(block.get("name") or "")):
                return True
    return False


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("stop_hook_active"):
        return 0

    transcript = payload.get("transcript_path") or ""
    message = perm.closing_of(payload)
    if not message or not claim.CLAIM.search(perm.unquoted(message)):
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    if not cycle_repo(cwd):
        return 0

    touched = dead.touched_files(transcript)
    root = os.path.normpath(cwd).replace("\\", "/").lower().rstrip("/") + "/"
    mine = [t for t in touched if t.startswith(root) or not os.path.isabs(t)]
    source = [t for t in mine
              if t.endswith(claim.SOURCE) and not dead.TEST_HINT.search(t)]
    if not source:
        return 0

    items = []
    if not any(t.endswith(DOC) for t in mine):
        items.append("  - no doc changed alongside the code. AGENTS.md, "
                     "project-context, a contract, or docs/ describes the "
                     "behavior that just moved.")
    if not reviewed(transcript):
        items.append("  - the review step has not run yet: /bmad-code-review, "
                     "or the reviewer agent on this diff.")
    if not items:
        return 0

    sys.stderr.write(REMINDER.format(items="\n".join(items)) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
