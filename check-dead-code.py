#!/usr/bin/env python3
"""Stop hook. Reads the diff, not the prose: did this session add a public
symbol that nothing outside its own file and its tests ever names?

A phrase list catches an agent that says it left work open. This catches the
one that does not say it. Exit 2 + stderr re-wakes the model with the list.
"""
import json
import os
import re
import subprocess
import sys

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

REMINDER = """STOP HOOK - DEAD CODE IN YOUR OWN DIFF

These symbols were added in this working tree and nothing outside their own
file and the tests ever names them:

{items}

Code with no caller ships zero value. Tests passing does not change that.
Take each one to a caller that actually runs - the composition root, the
refresh pass, the screen - before you report anything.

If a symbol is a genuine entry point (framework callback, serialized shape,
reflective use), say which and why in one line, and move on."""


def git(args, cwd):
    try:
        done = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


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


def orphans(cwd, symbols):
    dead = []
    for name, path in symbols.items():
        try:
            done = subprocess.run(
                ["git", "grep", "--untracked", "-l", "-w", "-e", name,
                 "--", ".", ":!*[Tt]est*", ":!*spec*"],
                cwd=cwd, capture_output=True, text=True, timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        hits = {h.replace("\\", "/") for h in done.stdout.split() if h}
        hits.discard(path.replace("\\", "/"))
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
    if not git(["rev-parse", "--is-inside-work-tree"], cwd).strip().startswith("true"):
        return 0

    touched = touched_files(payload.get("transcript_path") or "")
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
