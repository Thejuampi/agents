#!/usr/bin/env python3
"""Stop hook. The closing message says a file was created or a symbol deleted.
This asks the tree, one claim at a time.

Verifying these by hand is what caught a report that named a file as added.
It takes seconds per claim and nobody does it twice. The tree answers faster
and never gets tired.

Only claims naming a concrete file or symbol are checked. Prose stays prose.
"""
import json
import os
import re
import subprocess
import sys

TOKEN = r"`([\w./\\-]+)`"

CREATE_VERB = r"creado|creada|agregado|agregada|añadido|nuevo|nueva|new|added|created|written"
DELETE_VERB = (r"borrado|borrada|borr[eé]|eliminado|eliminada|elimin[eé]|"
               r"sacado|saqu[eé]|deleted|removed|gone")

CREATED = [
    re.compile(TOKEN + r"[^\n]{0,60}?\b(?:" + CREATE_VERB + r")\b", re.IGNORECASE),
    re.compile(r"\b(?:cre[eé]|agregu[eé]|añad[ií]|added|created|wrote)\b"
               r"[^\n]{0,60}?" + TOKEN, re.IGNORECASE),
]

DELETED = [
    re.compile(TOKEN + r"[^\n]{0,60}?\b(?:" + DELETE_VERB + r")\b", re.IGNORECASE),
    re.compile(r"\b(?:borr[eé]|elimin[eé]|saqu[é]|deleted|removed)\b"
               r"[^\n]{0,60}?" + TOKEN, re.IGNORECASE),
]

SKIP = {"main", "it", "run", "test", "tests", "true", "false", "null", "PRD", "README"}

REMINDER = """STOP HOOK - A CLAIM THE TREE DOES NOT BACK

Your closing message states these as fact and the working tree disagrees:

{items}

Every one takes seconds to check and the reader will not check them. That is
exactly why a wrong one survives to production.

Go look at each, fix the code or fix the sentence, and report what is there."""


def git(args, cwd):
    try:
        done = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def last_text(path):
    text = ""
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
                joined = " ".join(b.get("text", "") for b in content
                                  if isinstance(b, dict) and b.get("type") == "text").strip()
                if joined:
                    text = joined
    except OSError:
        return ""
    return text


def roots(transcript, cwd):
    """Every tree this turn actually wrote into, starting with the session cwd.

    A session is anchored to one repo and edits files outside it all the time -
    this hook itself lives in ~/.claude while the session runs in a project. A
    name resolved only against cwd is then reported as missing when it exists,
    which is the same false fact the hook exists to catch, published by the
    hook. The turn already says where it wrote; that is what is asked."""
    found = [cwd]
    for path in written(transcript):
        top = git(["rev-parse", "--show-toplevel"], os.path.dirname(path)).strip()
        if top and top not in found:
            found.append(top)
    return found


def written(transcript):
    seen = []
    try:
        with open(transcript, encoding="utf-8") as handle:
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
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    path = (block.get("input") or {}).get("file_path")
                    if isinstance(path, str) and os.path.exists(path) and path not in seen:
                        seen.append(path)
    except OSError:
        return []
    return seen


def touched(name, wrote):
    """The claim answered from the turn itself, with no tree involved.

    roots() needs the file to sit in a repo, and plenty of real work does not:
    a scratch directory, a dotfile tree nobody ever ran git init on. The turn
    already wrote the path down and the file is still on disk, so the claim is
    backed. This is the cheapest true answer available and it is checked first."""
    want = name.replace(chr(92), "/").strip("/")
    for path in wrote:
        flat = path.replace(chr(92), "/")
        if flat.endswith("/" + want) or os.path.basename(flat) == want:
            return True
    return False


def named(match):
    name = match.group(1)
    if not name or name in SKIP or len(name) <= 2 or name.isdigit():
        return None
    return name


def exists(cwd, name):
    if "/" in name or "\\" in name:
        return os.path.exists(os.path.join(cwd, name))
    if "." in name:
        return bool(git(["ls-files", "--cached", "--others", "--exclude-standard",
                         f"*{name}"], cwd).strip())
    return bool(git(["grep", "--untracked", "-l", "-w", "-e", name, "--", "."], cwd).strip())


def declared(cwd, name):
    """A deleted symbol must have no declaration left. A mention in a comment
    or inside a test name is not a declaration."""
    if "." in name or "/" in name or "\\" in name:
        return os.path.exists(os.path.join(cwd, name)) or bool(
            git(["ls-files", "--cached", "--others", "--exclude-standard", f"*{name}"],
                cwd).strip())
    pattern = r"(fun|val|const val|class|object|interface|def)\s+" + re.escape(name) + r"\b"
    try:
        done = subprocess.run(["git", "grep", "--untracked", "-l", "-E", pattern, "--", "."],
                              cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(done.stdout.strip())


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}

    if payload.get("stop_hook_active"):
        return 0

    transcript = payload.get("transcript_path") or ""
    if not transcript or not os.path.exists(transcript):
        return 0

    message = last_text(transcript)
    if not message:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    if not git(["rev-parse", "--is-inside-work-tree"], cwd).strip().startswith("true"):
        return 0

    wrote = written(transcript)
    trees = roots(transcript, cwd)

    bad = []
    for rx in CREATED:
        for match in rx.finditer(message):
            name = named(match)
            if name and not touched(name, wrote) and not any(
                    exists(root, name) for root in trees):
                bad.append(f"  {name}: reported as added, not in the tree")
    for rx in DELETED:
        for match in rx.finditer(message):
            name = named(match)
            if name and any(declared(root, name) for root in trees):
                bad.append(f"  {name}: reported as deleted, still there")

    seen = []
    for line in bad:
        if line not in seen:
            seen.append(line)
    if not seen:
        return 0

    sys.stderr.write(REMINDER.format(items="\n".join(seen[:10])) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
