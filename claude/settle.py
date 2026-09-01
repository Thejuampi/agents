#!/usr/bin/env python3
"""Runs the gate to a settled answer, the way a session reaches one.

A clean closing no longer ends the turn on the first pass: it earns one
question about the next action, and the release comes after the agent answers.
Tests that ask 'does the gate let this through' want the settled outcome, so
they run the chain instead of the first pass alone.

It runs the gate in this process. A suite used to start a fresh interpreter
for every case, several hundred of them, and on Windows each one opened a
console over whatever the developer was looking at. The gate is a function of
a payload on stdin and an exit code out, so the process bought nothing."""
import importlib.util
import io
import json
import os
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

gate = mod.load("check-stop.py")

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-stop.py")
ASK = "IS THERE SOMETHING WE CAN DO PROACTIVELY"


spawn = mod.load("spawn.py")


class Done:
    """What subprocess.run gives back, without the process."""

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def script(path, payload=None, env=None):
    """Run one hook in this process, as the harness would run it.

    A hook reads a payload on stdin, writes to stderr and returns an exit
    code. That is a function, and starting an interpreter for it was the
    whole cost of the suite."""
    module = mod.load(os.path.basename(path))
    out, said = io.StringIO(), io.StringIO()
    heard, wrote, spoke = sys.stdin, sys.stdout, sys.stderr
    before = dict(os.environ)
    if env is not None:
        os.environ.clear()
        os.environ.update(env)
    sys.stdin = io.StringIO(payload or "")
    sys.stdout, sys.stderr = out, said
    try:
        code = module.main() if hasattr(module, "main") else 0
    except SystemExit as done:
        code = done.code
    finally:
        sys.stdin, sys.stdout, sys.stderr = heard, wrote, spoke
        os.environ.clear()
        os.environ.update(before)
    return Done(code or 0, out.getvalue(), said.getvalue())


def run(command, input=None, env=None, **kw):
    """Drop-in for spawn.run that keeps a sibling hook in process."""
    parts = [str(part) for part in command]
    if (len(parts) == 2 and parts[0] == sys.executable
            and parts[1].endswith(".py")
            and os.path.dirname(os.path.abspath(parts[1])) == HERE):
        return script(parts[1], input, env)
    return spawn.run(command, input=input, env=env, **kw)


def once(payload, env=None, timeout=200):
    """One pass of the gate, with the environment the caller asked for."""
    said = io.StringIO()
    out = io.StringIO()
    heard, wrote, spoke = sys.stdin, sys.stdout, sys.stderr
    before = dict(os.environ)
    if env is not None:
        os.environ.clear()
        os.environ.update(env)
    sys.stdin = io.StringIO(json.dumps(payload))
    sys.stdout, sys.stderr = out, said
    try:
        code = gate.main()
    except SystemExit as done:
        code = done.code
    finally:
        sys.stdin, sys.stdout, sys.stderr = heard, wrote, spoke
        os.environ.clear()
        os.environ.update(before)
    return code or 0, said.getvalue()


def settled(payload, env=None, timeout=200):
    """The outcome once the proactive question has been answered."""
    code, err = once(payload, env, timeout)
    if ASK not in err:
        return code, err
    return once(dict(payload, stop_hook_active=True), env, timeout)
