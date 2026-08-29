#!/usr/bin/env python3
"""The cycle checker arms itself off the repo and only asks for what is missing."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_settle = importlib.util.spec_from_file_location(
    "_hook_settle", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "settle.py"))
settle = importlib.util.module_from_spec(_settle)
_settle.loader.exec_module(settle)

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")


HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-cycle.py")

RUNS = []

DONE = "Listo. La pantalla queda cableada y la suite corre entera, 0 fallas."

CYCLE_RULE = ("# Rules\n\nA requirement runs the closed cycle "
              "PRD -> spec -> build -> review, every step, every time.\n")


def counted():
    RUNS.append(None)


def repo(rule=CYCLE_RULE):
    root = tempfile.mkdtemp()
    if rule:
        with open(os.path.join(root, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write(rule)
    return root


def run(root, files=(), review=False, message=DONE):
    counted()
    blocks = [{"type": "tool_use", "name": "Write",
               "input": {"file_path": os.path.join(root, path)}} for path in files]
    if review:
        blocks.append({"type": "tool_use", "name": "Skill",
                       "input": {"skill": "bmad-code-review"}})
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8")
    with handle:
        handle.write(json.dumps({"type": "assistant",
                                 "message": {"content": blocks}}) + "\n")
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": message}]}}) + "\n")
    payload = json.dumps({"transcript_path": handle.name, "cwd": root,
                          "stop_hook_active": False})
    done = settle.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True)
    os.unlink(handle.name)
    return done.returncode, done.stderr


def main():
    failures = []

    code, err = run(repo(), files=["src/Screen.kt"])
    if code != 2:
        failures.append("code with no docs and no review must fire")
    elif "no doc changed" not in err or "review step has not run" not in err:
        failures.append(f"both gaps must be named: {err[:160]}")

    code, err = run(repo(), files=["src/Screen.kt", "docs/screen.md"])
    if code != 2:
        failures.append("docs without a review must fire")
    elif "no doc changed" in err:
        failures.append("a doc that changed must not be reported missing")

    code, err = run(repo(), files=["src/Screen.kt"], review=True)
    if "review step has not run" in err:
        failures.append("a review that ran must not be reported missing")

    code, err = run(repo(), files=["src/Screen.kt", "AGENTS.md"], review=True)
    if code != 0:
        failures.append(f"docs and review together must stay silent: {err[:160]}")

    code, err = run(repo(rule=""), files=["src/Screen.kt"])
    if code != 0:
        failures.append("a repo that never adopted the cycle must not pay for it")

    code, err = run(repo(rule="# Rules\n\nBMAD is a menu, not a pipeline.\n"),
                    files=["src/Screen.kt"])
    if code != 0:
        failures.append("a repo that calls BMAD a menu must stay untouched")

    code, err = run(repo(), files=["docs/only.md"])
    if code != 0:
        failures.append("a docs-only turn is not a requirement build")

    code, err = run(repo(), files=["src/test/ScreenTest.kt"])
    if code != 0:
        failures.append("test-only work is not a requirement build")

    code, err = run(repo(), files=["src/Screen.kt"],
                    message="Voy por la mitad, sigo con el resto.")
    if code != 0:
        failures.append("no completion claim must stay silent")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
