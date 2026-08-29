#!/usr/bin/env python3
"""Tests that need the 9B judge, and only run when somebody asks for them.

A judge test loads 5.5GB into the card and several gigabytes of RAM. Paying
that on every suite run, while iterating on a checker that never talks to the
model, cost this machine a reboot on 2026-08-29. The heavy checks belong at
delivery, like the git ones."""
import os
import sys

FLAG = "STOP_TEST_LIVE"


def wanted():
    return os.environ.get(FLAG) == "1"


def skip(cases=0):
    print(f"{cases} cases, 0 failures "
          f"(judge tests skipped, set {FLAG}=1 to run them)")
    sys.exit(0)
