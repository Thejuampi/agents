#!/usr/bin/env python3
"""The suite's process budget, pinned.

Process count is what made the machine unusable, so it is a number the suite
has to defend rather than a habit somebody keeps. The ledger counts every
child started through spawn.py; a test that adds a process to the common path
has to raise this on purpose."""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET = 60


def load(alias, filename):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spawn = load("spawn", "spawn.py")


def main():
    failures = []
    cases = 0

    cases += 1
    ledger = tempfile.NamedTemporaryFile(suffix=".log", delete=False).name
    os.environ[spawn.LEDGER] = ledger
    spawn.run([sys.executable, "-c", "pass"])
    del os.environ[spawn.LEDGER]
    written = open(ledger, encoding="utf-8").read().strip()
    os.unlink(ledger)
    if not written:
        failures.append("a child started here must be written down")

    cases += 1
    used = os.environ.get("STOP_SPAWN_COUNT")
    if used and int(used) > BUDGET:
        failures.append(f"the suite spent {used} processes, budget is {BUDGET}")

    print(f"{cases} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
