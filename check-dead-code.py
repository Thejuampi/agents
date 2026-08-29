#!/usr/bin/env python3
"""Stop hook. Reads the diff, not the prose: did this session add a public
symbol that nothing outside its own file and its tests ever names?

A phrase list catches an agent that says it left work open. This catches the
one that does not say it. Exit 2 + stderr re-wakes the model with the list.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")
claim = mod.load("claim.py")
perm = mod.load("check-permission.py")


KOTLIN = re.compile(
    r"^\+(?:@\w+(?:\([^)]*\))?\s+)*"
    r"(?!.*\b(?:private|internal|override|operator|actual)\b)"
    r"(?:public\s+|open\s+|abstract\s+|sealed\s+|data\s+|value\s+|suspend\s+|inline\s+)*"
    r"(?:fun|class|object|interface|enum\s+class|val|const\s+val)\s+"
    r"(?:<[^>]*>\s*)?"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)

PYTHON = re.compile(r"^\+(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
TS = re.compile(r"^\+export\s+(?:async\s+)?(?:function|class|const|interface|type)\s+([A-Za-z_$][\w$]*)")

TEST_HINT = re.compile(r"(^|[/\\])(test|tests|__tests__)([/\\]|$)|[Tt]est\.\w+$|_test\.\w+$|\.spec\.\w+$")

PATH_LIKE = re.compile(r"[\w./\:-]+\.(?:kt|java|py|ts|tsx)")

SKIP_NAMES = {"main", "invoke", "toString", "equals", "hashCode", "copy", "it", "run"}

REMINDER = """KEEP GOING - THIS CODE HAS NOBODY CALLING IT YET

{items}

The piece itself is fine. Nothing outside its own file and its tests names it, so a reader cannot see it work. Wire it to the visible end in this same turn, or drop it - you are one step from having it count."""


def inside_repo(cwd):
    """Whether this is a work tree, asked of the disk.

    rev-parse answers the same question and costs a process. On Windows the
    git wrapper starts children of its own, and those do not inherit the flag
    that keeps a console hidden, so every stop flashed windows over the
    editor. A directory walk is free and cannot flash anything."""
    here = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.exists(os.path.join(here, ".git")):
            return True
        parent = os.path.dirname(here)
        if parent == here:
            return False
        here = parent


ASKED = {}
"""One answer per question per stop.

The checkers share this interpreter now, so the same question asked twice is
the same process started twice. A stop was running rev-parse once for every
caller that wanted to know it was in a repository."""


def git(args, cwd):
    key = (tuple(args), cwd)
    if key in ASKED:
        return ASKED[key]
    try:
        done = spawn.run(["git"] + args, cwd=cwd, capture_output=True,
                         text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        ASKED[key] = ""
        return ""
    ASKED[key] = done.stdout if done.returncode == 0 else ""
    return ASKED[key]


WRITERS = {"write", "edit", "multiedit",
           "notebookedit", "bash", "powershell"}
"""Tools that can leave a file different from how they found it.

This counted any call carrying a file_path, and Read carries one. A turn
that only looked at code was read as a turn that wrote it, which is wrong on
its own terms and made every such stop run git for nothing."""


def touched_files(path):
    """Files this session actually wrote. Another agent on the same tree is not mine."""
    touched = set()
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                content = entry.get("message", {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    if str(block.get("name") or "").lower() not in WRITERS:
                        continue
                    payload = block.get("input") or {}
                    target = payload.get("file_path")
                    if isinstance(target, str):
                        touched.add(os.path.normpath(target).replace("\\", "/").lower())
                    # Edits made through the shell carry no file_path, so the
                    # command text is the only record of what they touched.
                    command = payload.get("command")
                    if isinstance(command, str):
                        for token in PATH_LIKE.findall(command):
                            touched.add(os.path.normpath(token).replace("\\", "/").lower())
    except OSError:
        return set()
    return touched


def mine(path, cwd, touched):
    """No record of writing anything means nothing here is mine. Two sessions
    share this tree, and the transcript is a file another process is still
    appending to - a read that comes back empty is missing evidence, not proof
    of authorship. Blaming a session for code it never touched is the fastest
    way to teach it that the hook is noise."""
    if not touched:
        return False
    norm = path.replace("\\", "/").lower()
    full = os.path.normpath(os.path.join(cwd, path)).replace("\\", "/").lower()
    return any(t == full or t == norm or full.endswith("/" + t) or t.endswith("/" + norm)
               for t in touched)


def added_symbols(cwd, touched):
    diff = git(["diff", "HEAD", "--unified=0"], cwd)
    untracked = git(["ls-files", "--others", "--exclude-standard"], cwd).split()
    found = {}
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if not line.startswith("+") or TEST_HINT.search(current):
            continue
        if not mine(current, cwd, touched):
            continue
        for pattern in (KOTLIN, PYTHON, TS):
            match = pattern.match(line)
            if match:
                found.setdefault(match.group(1), current)
                break
    for path in untracked:
        if TEST_HINT.search(path) or not path.endswith((".kt", ".java", ".py", ".ts", ".tsx")):
            continue
        if not mine(path, cwd, touched):
            continue
        try:
            with open(os.path.join(cwd, path), encoding="utf-8", errors="ignore") as handle:
                for raw in handle:
                    for pattern in (KOTLIN, PYTHON, TS):
                        match = pattern.match("+" + raw.rstrip("\n"))
                        if match:
                            found.setdefault(match.group(1), path)
                            break
        except OSError:
            continue
    return {n: p for n, p in found.items() if n not in SKIP_NAMES and len(n) > 2}


BATCH = 60
"""How many symbols go into one git grep.

This asked git once per symbol, and a turn is allowed to add 120 of them, so
a single stop could start 120 processes. git takes as many patterns as you
give it; the line number comes back with each hit, which is enough to say
which symbol was found where."""


def orphans(cwd, symbols):
    names = list(symbols)
    seen = {name: set() for name in names}
    for start in range(0, len(names), BATCH):
        chunk = names[start:start + BATCH]
        args = ["git", "grep", "--untracked", "-n", "-w"]
        for name in chunk:
            args += ["-e", name]
        args += ["--", ".", ":!*[Tt]est*", ":!*spec*"]
        try:
            done = spawn.run(args, cwd=cwd, capture_output=True, text=True,
                             timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        for line in done.stdout.splitlines():
            path, _, rest = line.partition(":")
            _, _, text = rest.partition(":")
            for name in chunk:
                if re.search(r"\b" + re.escape(name) + r"\b", text):
                    seen[name].add(path.replace(chr(92), "/"))

    dead = []
    for name, path in symbols.items():
        hits = set(seen.get(name) or ())
        hits.discard(path.replace(chr(92), "/"))
        if not hits:
            dead.append(f"  {name}  ({path})")
    return dead


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}

    if payload.get("stop_hook_active"):
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    message = perm.last_assistant_text(payload.get("transcript_path") or "")
    if not message or not claim.CLAIM.search(perm.unquoted(message)):
        return 0

    if not inside_repo(cwd):
        return 0

    touched = touched_files(payload.get("transcript_path") or "")
    if not touched:
        return 0

    symbols = added_symbols(cwd, touched)
    if not symbols or len(symbols) > 120:
        return 0

    dead = orphans(cwd, symbols)
    if not dead:
        return 0

    sys.stderr.write(REMINDER.format(items="\n".join(sorted(dead)[:20])) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
