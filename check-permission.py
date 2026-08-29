#!/usr/bin/env python3
"""Stop hook. One question: did the final message announce the next step
instead of doing it, or ask for permission that was already granted?

Exit 2 + stderr -> the harness re-wakes the model with the reminder in context.
Exit 0 silent   -> nothing to say.

Nothing about the rules lives in this file. The patterns come from
stop-patterns.txt beside it, and a repo can add or remove its own at
<repo>/.claude/stop-patterns.txt. The sources the reminder points at are
whatever the repo actually holds, discovered per run, so a project with no PRD
gets told to read its README and its tests instead.

There is no escape hatch here. Blockers are handled once, centrally, in
check-stop.py, behind a release phrase and the local model. A checker that let
the string BLOCKED: through was a checker that could be switched off by typing
it.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATTERNS = os.path.join(HERE, "stop-patterns.txt")

FENCED = re.compile(r"```.*?```", re.DOTALL)
CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile("\"[^\"\n]*\"|«[^»\n]*»|“[^”\n]*”")


REPORTED = re.compile(
    r"\b(dice|dicen|avisa|avisan|indica|indican|advierte|advierten|aclara|explica|"
    r"muestra|reza|says|warns|reads|states|tells)\s+(que|that)\b[^.\n]*",
    re.IGNORECASE,
)


def unquoted(message, code=True):
    """The agent's own words. Reporting a phrase is not saying it, so anything
    fenced, backticked, quoted or attributed to something else comes out.
    One pass cannot do this: a backtick inside a quoted span eats the closing
    quote and leaks the rest of the line back in.

    Pass code=False when backticks do not mean attribution. An agent writes
    its own measurements as `2118 tests` all day; dropping those would hand it
    a way to launder every number it never ran."""
    plain = FENCED.sub(" ", message)
    if code:
        plain = CODE.sub(" ", plain)
    return REPORTED.sub(" ", QUOTED.sub(" ", plain))

REMINDER = """STOP HOOK - YOU DO NOT NEED PERMISSION

Your closing message matched: {hits}

You have permission already. It was granted in advance and it does not expire.
Do not announce the next step. Do it. Do not ask whether to proceed. Proceed.
Do not hand the work back as a menu of options. Pick one and build it.
Do not send the user to run something you can run yourself.

Do not ask for what this repo already answers. Read it:
{sources}

Do not close a turn reporting that nothing happened. Go find the work.

Changes can be reverted. Mistakes can be fixed. Time never comes back.
A stop spends the only thing that cannot be recovered.

Go back and do the work you just described. Report when it runs."""


def read_patterns(path):
    """Returns (added, removed). A line starting with - removes an inherited one."""
    added, removed = [], set()
    try:
        with open(path, encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                drop = line.startswith("-")
                if drop:
                    line = line[1:].strip()
                if ":" not in line:
                    continue
                label, _, pattern = line.partition(":")
                pattern = pattern.strip()
                if not pattern:
                    continue
                if drop:
                    removed.add(pattern)
                else:
                    added.append((label.strip(), pattern))
    except OSError:
        return [], set()
    return added, removed


def patterns_for(cwd):
    added, removed = read_patterns(BASE_PATTERNS)
    extra, extra_removed = read_patterns(os.path.join(cwd, ".claude", "stop-patterns.txt"))
    added += extra
    removed |= extra_removed
    out = []
    for label, pattern in added:
        if pattern in removed:
            continue
        try:
            out.append((label, re.compile(pattern, re.IGNORECASE)))
        except re.error:
            continue
    return out


NOISE = ("/build/", "/dist/", "/target/", "/out/", "/bin/", "/obj/",
         "/node_modules/", "/.git/", "/.gradle/", "/.idea/", "/venv/",
         "/__pycache__/", "/coverage/", "/.next/", "/vendor/")

CHECKS = [
    ("the spec", ["*[Pp][Rr][Dd]*.md", "docs/**/*[Pp][Rr][Dd]*.md",
                  "spec/**/*.md", "specs/**/*.md", "requirements*.md",
                  "_bmad-output/**/*.md"]),
    ("the README", ["README*", "readme*"]),
    ("the project instructions", ["CLAUDE.md", "AGENTS.md", ".cursorrules",
                                  ".github/copilot-instructions.md"]),
    ("the docs", ["docs/**/*.md", "doc/**/*.md"]),
    ("the tests", ["**/src/test/**", "**/tests/**", "**/test/**",
                   "**/*_test.*", "**/*.spec.*", "**/[Tt]est*.*"]),
]


def _pick(cwd, pattern):
    """The shortest match, which is the canonical one. A repo has one README
    at the root and forty in its dependencies."""
    try:
        hits = [p for p in glob.iglob(os.path.join(cwd, pattern), recursive=True)
                if not any(n in p.replace("\\", "/") + "/" for n in NOISE)]
    except OSError:
        return None
    if not hits:
        return None
    return min(hits, key=lambda p: (len(p.split(os.sep)), len(p)))


def sources_in(cwd):
    """What this repo actually offers to read, discovered per run. A project
    with no spec is told to read its README and its tests instead. Nothing
    about any one project is written down here."""
    found = []
    for label, globs in CHECKS:
        for pattern in globs:
            hit = _pick(cwd, pattern)
            if hit:
                found.append((label, os.path.relpath(hit, cwd).replace("\\", "/")))
                break
    found.append(("the git history", "git log"))
    found.append(("the running app", "build it and use it"))
    return "\n".join(f"  - {label}: {where}" for label, where in found)


def last_assistant_text(path):
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
                parts = [b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text"]
                joined = " ".join(p for p in parts if p).strip()
                if joined:
                    text = joined
    except OSError:
        return ""
    return text


def prose(message):
    """The message with code removed. A question followed by the code it
    proposes is still a question waiting for an answer, and a regex quoted
    inside backticks is not a question however it ends."""
    out = []
    fenced = False
    for line in message.strip().splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(CODE.sub(" ", line))
    return "\n".join(out)


def ends_on_a_question(message):
    """The shape, not the vocabulary. A closing question hands the turn back
    whatever words it uses, so this catches phrasings no list foresees.

    The whole last paragraph counts, not only its last line. Asking the
    question and then adding a sentence of colour does not unask it."""
    body = prose(message).strip()
    if not body:
        return False
    closing = []
    for line in reversed(body.splitlines()):
        stripped = line.strip().strip("*_`> ")
        if not stripped:
            if closing:
                break
            continue
        closing.insert(0, stripped)
        if len(closing) >= 3:
            break
    return any(sentence.strip().endswith("?")
               for line in closing
               for sentence in re.split(r"(?<=[.!?])\s+", line))


def acted_this_turn(path):
    """Did any tool run since the user last spoke? A turn of pure prose that
    closes short is an acknowledgement, and an acknowledgement is not work."""
    used = False
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") == "user":
                    content = entry.get("message", {}).get("content")
                    if not isinstance(content, list) or any(
                            isinstance(b, dict) and b.get("type") != "tool_result"
                            for b in content):
                        used = False
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = entry.get("message", {}).get("content")
                if isinstance(content, list) and any(
                        isinstance(b, dict) and b.get("type") == "tool_use" for b in content):
                    used = True
    except OSError:
        return True
    return used


def ends_on_nothing(message, acted):
    """Short, no tools, turn over. The work was available and went untouched."""
    return not acted and len(message.strip()) < 400


MAYBE = 3
"""Exit code for a hit nobody should be sentenced on.

A pattern matches a word and cannot see around it: "nothing pending" trips the
pending rule, "no deja nada pendiente" reads as an announcement. Those wordings
are worth catching and are not worth blocking on their own, so they leave here
as a candidate and the local model decides. A class written with a trailing ?
in stop-patterns.txt is one of these. Everything else still blocks on its own,
which is most of the list: a direct request for permission needs no second
opinion."""


def weak(label):
    return label.rstrip().endswith("?")


def offenders(message, cwd=None, acted=True):
    # Naming a trigger phrase is not using it. Talking about the hook, or
    # quoting someone, must not fire it.
    stripped = unquoted(message)
    hits = [f"{label}: {rx.pattern}" for label, rx in patterns_for(cwd or os.getcwd())
            if rx.search(stripped)]
    if ends_on_a_question(message):
        hits.append("shape: closing question")
    if ends_on_nothing(message, acted):
        hits.append("shape: a short turn that ran nothing")
    return hits


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

    message = last_assistant_text(transcript)
    if not message:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    hits = offenders(message, cwd, acted_this_turn(transcript))
    if not hits:
        return 0

    sys.stderr.write(REMINDER.format(hits=", ".join(hits[:5]), sources=sources_in(cwd)) + "\n")
    return MAYBE if all(weak(h.split(chr(58))[0]) for h in hits) else 2


if __name__ == "__main__":
    sys.exit(main())
