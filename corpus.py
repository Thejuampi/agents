#!/usr/bin/env python3
"""Builds the labelled corpus of closings, and says how the gate scores on it.

A closing is the last thing the agent wrote before the developer spoke again.
The label is what the developer said next, judged PUSH or NEW by a second
model that never sees the gate's opinion.

The first build of this corpus counted the gate's own reminder as the
developer speaking. That did two things, both wrong. It handed the reminder to
the push judge as if a person had written it, and 9 of the 123 positives were
the gate scoring its own text. It also cut the window at every block, so work
the agent did after being woken was credited to a new closing instead of the
one that earned the block. A wake is the system talking to itself and is
skipped here on both counts."""
import glob
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.expanduser("~/.claude/projects")
OUT = os.path.join(HERE, "corpus.json")
WAKE = "Stop hook feedback:"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perm = load("perm", "check-permission.py")
gate = load("gate", "check-stop.py")
judge = load("judge", "llm_judge.py")
push = load("push", "judge_push.py")


def entries(path):
    try:
        handle = open(path, encoding="utf-8")
    except OSError:
        return []
    rows = []
    with handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                rows.append(entry)
    return rows


def text_of(entry):
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return " ".join(
        block.get("text", "") for block in content
        if isinstance(block, dict) and block.get("type") == "text").strip()


def spoke(entry):
    """The developer, never a tool result and never this gate's own wake."""
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return WAKE not in content[:200]
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") != "tool_result"
        for block in content)


def tools(entry):
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return 0
    return sum(1 for block in content
               if isinstance(block, dict) and block.get("type") == "tool_use")


def pairs():
    out = []
    for path in sorted(glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))):
        closing, asked, used, blocks = "", "", 0, 0
        for entry in entries(path):
            if spoke(entry):
                body = text_of(entry)
                if closing and body and not body.startswith("<"):
                    out.append({"closing": closing, "next": body,
                                "asked": asked, "tools": used,
                                "blocks": blocks, "file": path})
                asked, closing, used, blocks = body, "", 0, 0
                continue
            if entry.get("type") == "user":
                if WAKE in str(text_of(entry))[:200]:
                    blocks += 1
                continue
            if entry.get("type") != "assistant":
                continue
            used += tools(entry)
            body = text_of(entry)
            if body:
                closing = body
    return out


def label(rows, step=50):
    start = time.time()
    for i, row in enumerate(rows):
        if i % step == 0:
            print(i, int(time.time() - start), "s", flush=True)
        message = row["closing"]
        row["noise"] = bool(gate.harness_noise(message))
        if row["noise"]:
            continue
        row["push"] = push.pushed(message, row["next"])
        hits = perm.offenders(message, HERE, row["tools"] > 0)
        row["hits"] = hits
        row["firm"] = [h for h in hits
                       if not h.split(":")[0].rstrip().endswith("?")]
        verdict, _ = judge.stop_verdict(message, asked=row["asked"])
        row["verdict"] = verdict if isinstance(verdict, str) else None
        row["fired"] = bool(row["firm"]) or row["verdict"] == "STOP"
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = pairs()
    print(len(rows), "closings", flush=True)
    label(rows)
    json.dump(rows, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False)
    real = [r for r in rows if not r.get("noise")]
    hit = [r for r in real if r.get("push")]
    fired = [r for r in real if r.get("fired")]
    caught = [r for r in fired if r.get("push")]
    print(f"{len(real)} non-noise, {len(hit)} pushes ({100.0 * len(hit) / max(len(real), 1):.1f}%)")
    print(f"gate fires {len(fired)} prec {len(caught) / max(len(fired), 1):.3f} rec {len(caught) / max(len(hit), 1):.3f}")


if __name__ == "__main__":
    main()
