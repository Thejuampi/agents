#!/usr/bin/env python3
"""Runs the gate to a settled answer, the way a session reaches one.

A clean closing no longer ends the turn on the first pass: it earns one
question about the next action, and the release comes after the agent answers.
Tests that ask 'does the gate let this through' want the settled outcome, so
they run the chain instead of the first pass alone."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-stop.py")
ASK = "IS THERE SOMETHING WE CAN DO PROACTIVELY"


def once(payload, env, timeout=200):
    done = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                          capture_output=True, text=True, env=env,
                          timeout=timeout)
    return done.returncode, done.stderr


def settled(payload, env=None, timeout=200):
    """The outcome once the proactive question has been answered."""
    env = env or dict(os.environ)
    code, err = once(payload, env, timeout)
    if ASK not in err:
        return code, err
    return once(dict(payload, stop_hook_active=True), env, timeout)
