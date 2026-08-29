#!/usr/bin/env python3
"""Grades the turns the gate let end, which the daily report cannot see.

judge-report.py reads the log, so it only ever grades blocks. A turn allowed
through is written nowhere and looked at by nobody, and that is exactly where
a gate goes quietly blind.

This walks the transcripts instead of the log. For every turn the gate
allowed, it asks whether the developer's next message was a push. A push
after an allowed turn is a miss: the agent stopped early and the gate agreed
with it.

It costs one model call per exchange, so it is run on demand rather than at
session start."""
import glob
import importlib.util
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "transcript", os.path.join(HERE, "transcript.py"))
reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reader)
PROJECTS = os.path.expanduser("~/.claude/projects")


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stop = load("stop", "check-stop.py")
perm = load("perm", "check-permission.py")
push = load("push", "judge_push.py")


spoke = reader.spoke


def said(entry):
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return " ".join(b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text").strip()


def exchanges(path):
    closing = ""
    for entry in stop.entries(path):
        if spoke(entry):
            reply = said(entry)
            if closing and reply and not reply.startswith("<"):
                yield closing, reply
            closing = ""
            continue
        if entry.get("type") == "assistant":
            text = said(entry)
            if text:
                closing = text


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    allowed, missed, seen = 0, [], 0
    for path in sorted(glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))):
        for closing, reply in exchanges(path):
            if seen >= limit:
                break
            seen += 1
            if stop.harness_noise(closing) or perm.offenders(closing):
                continue
            allowed += 1
            if push.pushed(closing, reply):
                missed.append((closing, reply))
        if seen >= limit:
            break

    if not allowed:
        print("no allowed turns found")
        return 0
    print(f"{allowed} turns the patterns let through, {len(missed)} of them "
          f"got pushed ({100.0 * len(missed) / allowed:.1f}%)")
    for closing, reply in missed[:8]:
        print("  ->", " ".join(closing.split())[:70])
        print("     user:", " ".join(reply.split())[:60])
    return 0


if __name__ == "__main__":
    sys.exit(main())
