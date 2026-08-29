#!/usr/bin/env python3
"""Stop hook. The closing message says the work is done. This asks the tree
and the session log whether that is true.

A green unit suite proves the code compiles under the test task. It does not
prove the app builds, that anyone ran it, that a real endpoint answered, or
that the work exists anywhere but this machine. Claiming "done" on that
evidence hands the user a bill they only find at the next release.

Fires only when the message makes a completion claim AND this session wrote
non-test source. Exit 2 + stderr re-wakes the model with what is missing.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("dead", os.path.join(HERE, "check-dead-code.py"))
dead = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dead)

FENCED = re.compile(r"```.*?```", re.DOTALL)
CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile("\"[^\"\n]*\"|«[^»\n]*»|“[^”\n]*”")


def unquoted(message):
    """Quoting somebody's done claim is not making one. Fences come out first:
    a backtick inside a quoted span swallows the closing quote."""
    return QUOTED.sub(" ", CODE.sub(" ", FENCED.sub(" ", message)))

CLAIM = re.compile(
    r"\blisto\b|\bqueda (listo|cerrado|cableado)|cerrado y|cableado hasta|"
    r"\bterminad[oa]\b|\bcompleto\b|suite completa|0 fallas|0 failures|"
    r"todo verde|all green|\bship(ped|s)?\b|de punta a punta|"
    r"\bdone\b|\bit works\b|ya funciona|funciona\b.{0,20}\bahora\b|"
    r"\bexit 0\b|build successful",
    re.IGNORECASE,
)

BUILD = re.compile(
    r"assemble|:app:build|gradlew[^\n|;]*\bbuild\b|npm run build|yarn build|"
    r"cargo build|mvn[^\n|;]*package|dotnet build|\bmake\b|tsc\b|go build",
    re.IGNORECASE,
)

RUN = re.compile(
    r"\badb\s+(install|shell)|installDebug|emulator|flutter run|npm (run )?start|"
    r"docker run|gradlew[^\n|;]*\brun\b|\bpytest\b|\bcargo run\b|\bdotnet run\b",
    re.IGNORECASE,
)

FETCH = re.compile(r"\b(curl|wget|httpie|http)\b[^\n]*?(https?://|localhost|127\.0\.0\.1)",
                   re.IGNORECASE)

FIXTURE_SINK = re.compile(
    r"(-o|--output|-O|>)\s*\S*(src[/\\]test|test[/\\]resources|__fixtures__|"
    r"fixtures?[/\\]|testdata[/\\]|golden[/\\])",
    re.IGNORECASE,
)


def live(command):
    """A call to a real host answers a question fixtures cannot. Downloading
    one straight into test resources only refills the fixtures."""
    return bool(FETCH.search(command)) and not FIXTURE_SINK.search(command)

SCRIPT = re.compile(r"\b(?:python[\d.]*|node|ruby|perl|sh|bash)\s+(\S+\.(?:py|js|ts|rb|pl|sh))")

HEREDOC = re.compile(r"<<-?\s*'?\"?(\w+)'?\"?.*?^\1", re.DOTALL | re.MULTILINE)


def steps(command):
    """The commands actually invoked, without their arguments. A grep whose
    pattern contains the word assemble did not build anything."""
    body = HEREDOC.sub(" ", command)
    out = []
    for chunk in re.split(r"&&|\|\||;|\||\n", body):
        head = re.split(r"[\"']", chunk, maxsplit=1)[0]
        if head.strip():
            out.append(head)
    return out

SOURCE = (".kt", ".java", ".py", ".ts", ".tsx", ".swift", ".go", ".rs", ".cs")


def exercised(head, root):
    """Did this command exercise the product? A throwaway script under /tmp and a
    curl that fetches a fixture answer questions about the world, not about the
    thing being shipped."""
    if RUN.search(head):
        return True
    found = SCRIPT.search(head)
    if not found:
        return False
    target = found.group(1).replace("\\", "/")
    if os.path.isabs(target) or target.startswith("~"):
        return target.lower().startswith(root)
    return "/tmp/" not in target.lower() and not target.lower().startswith("../")

REMINDER = """STOP HOOK - YOU CALLED IT DONE AND THE TREE DISAGREES

Your closing message claims the work is finished. Missing evidence:

{gaps}

Green unit tests prove the code compiles under the test task. They do not
prove the app builds, that anybody ran it, that a live endpoint answered, or
that the work survives this machine. A report that skips those is a bill the
user only sees at release.

Close the gaps yourself, now, before you report again. Run the build. Run the
app or hit the real endpoint. Commit what you wrote. Then say what happened.

If a gap is genuinely out of reach here - no device, no credentials, no
network - say so with the release phrase the Stop hook issued, and the one
thing you need. It is then audited. Do not reach for it to close a gap you
could close yourself."""


def commands(path):
    """Every shell command this session ran. The record of what was verified."""
    out = []
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
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        command = (block.get("input") or {}).get("command")
                        if isinstance(command, str):
                            out.append(command)
    except OSError:
        return []
    return out


def uncommitted(cwd, touched):
    status = dead.git(["status", "--porcelain", "-uall"], cwd)
    pending = []
    for line in status.splitlines():
        path = line[3:].strip().strip('"')
        if not path.endswith(SOURCE) or dead.TEST_HINT.search(path):
            continue
        if dead.mine(path, cwd, touched):
            pending.append(path)
    return pending


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}

    if payload.get("stop_hook_active"):
        return 0

    transcript = payload.get("transcript_path") or ""
    spec2 = importlib.util.spec_from_file_location(
        "perm", os.path.join(HERE, "check-permission.py"))
    perm = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(perm)
    message = perm.last_assistant_text(transcript)
    if not message:
        return 0
    if not CLAIM.search(unquoted(message)):
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    if not dead.git(["rev-parse", "--is-inside-work-tree"], cwd).strip().startswith("true"):
        return 0

    touched = dead.touched_files(transcript)
    root = os.path.normpath(cwd).replace("\\", "/").lower().rstrip("/") + "/"
    wrote_source = [t for t in touched
                    if t.endswith(SOURCE) and not dead.TEST_HINT.search(t)
                    and (t.startswith(root) or not os.path.isabs(t))]
    if not wrote_source:
        return 0

    ran = commands(transcript)
    gaps = []
    heads = [h for c in ran for h in steps(c)]
    if not any(BUILD.search(h) for h in heads):
        gaps.append("  - the build never ran. A test task is not a build.")
    if not any(exercised(h, root) for h in heads) and not any(live(c) for c in ran):
        gaps.append("  - nothing ran the app or touched a live endpoint. "
                    "Fixtures answer the questions you already knew.")
    pending = uncommitted(cwd, touched)
    if pending:
        shown = ", ".join(sorted(pending)[:6])
        gaps.append(f"  - {len(pending)} source file(s) you wrote are uncommitted: {shown}")

    if not gaps:
        return 0

    sys.stderr.write(REMINDER.format(gaps="\n".join(gaps)) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
