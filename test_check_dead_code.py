#!/usr/bin/env python3
"""Builds throwaway git repos and checks the dead-code hook on each."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_seed = importlib.util.spec_from_file_location(
    "_hook_seed", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "seedrepo.py"))
seedrepo = importlib.util.module_from_spec(_seed)
_seed.loader.exec_module(seedrepo)

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
HOOK = os.path.join(HERE, "check-dead-code.py")

ORPHAN = "package a\n\nfun orphanedHelper(x: Int): Int = x + 1\n"
CALLER = "package a\n\nfun orphanedHelper(x: Int): Int = x + 1\n"
USER = "package a\n\nfun main() {\n    println(orphanedHelper(1))\n}\n"
TEST_ONLY = "package a\n\nimport kotlin.test.Test\n\nclass ThingTest {\n    @Test fun t() { orphanedHelper(1) }\n}\n"
LOCALS = "package a\n\nfun main() {\n    var scoredRows = listOf(1)\n    println(scoredRows)\n}\n"


def repo(files):
    return seedrepo.seeded(files)


CLAIM = "Listo. La suite corre completa, 0 fallas."


def log(root, written, claim=CLAIM):
    """The session record. Two agents share a tree, so a checker that blames
    on nothing but the diff blames the wrong one."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    blocks = [{"type": "tool_use", "name": "Write",
               "input": {"file_path": os.path.join(root, name)}} for name in written]
    blocks.append({"type": "text", "text": claim})
    handle.write(json.dumps({"type": "assistant", "message": {"content": blocks}}) + "\n")
    handle.close()
    return handle.name


def run(root, written=None, claim=CLAIM):
    path = log(root, written, claim) if written is not None else ""
    payload = json.dumps({"cwd": root, "transcript_path": path, "stop_hook_active": False})
    done = settle.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    if path:
        os.unlink(path)
    return done.returncode, done.stdout + done.stderr


CASES = [
    ("orphan is flagged", {"src/main/a/Thing.kt": ORPHAN}, 2, "orphanedHelper"),
    ("caller clears it", {"src/main/a/Thing.kt": CALLER, "src/main/a/Main.kt": USER}, 0, ""),
    ("only a test caller still counts as dead",
     {"src/main/a/Thing.kt": CALLER, "src/test/a/ThingTest.kt": TEST_ONLY}, 2, "orphanedHelper"),
    ("locals are not symbols", {"src/main/a/Main.kt": LOCALS}, 0, ""),
    ("clean tree says nothing", {}, 0, ""),
    ("python private stays unnamed",
     {"src/hidden.py": "def _hidden():\n    return 1\n"}, 0, ""),
    ("python public helper is dead until called",
     {"src/visible.py": "def visibleHelper():\n    return 2\n"}, 2, "visibleHelper"),
]


def main():
    failures = []
    for name, files, want_code, want_text in CASES:
        root = repo(files)
        code, out = run(root, written=list(files))
        if code != want_code:
            failures.append(f"{name}: exit {code}, wanted {want_code}\n{out}")
        elif want_text and want_text not in out:
            failures.append(f"{name}: missing {want_text!r} in output")

    root = repo({"src/main/a/Thing.kt": ORPHAN})
    code, out = run(root, written=["src/main/a/Thing.kt"], claim="Escribi el helper, sigo con el caller.")
    if code != 0:
        failures.append(f"a turn that is still iterating pays nothing: {out[:160]}")

    root = repo({"src/main/a/Thing.kt": ORPHAN})
    code, out = run(root, written=["src/main/a/Other.kt"])
    if code != 0:
        failures.append(f"another session's orphan is not mine: {out[:160]}")

    root = repo({"src/main/a/Thing.kt": ORPHAN})
    code, out = run(root, written=[])
    if code != 0:
        failures.append(f"no record of writing anything must stay silent: {out[:160]}")

    root = repo({"src/main/a/Thing.kt": ORPHAN})
    payload = json.dumps({"cwd": root, "stop_hook_active": True})
    done = settle.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    if done.returncode != 0:
        failures.append("stop_hook_active must never re-fire")

    print(f"{len(CASES) + 3} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
