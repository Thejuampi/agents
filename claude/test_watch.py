#!/usr/bin/env python3
"""The watcher has to name the process that opened the window, or it is a rumour.

The investigation it exists for ended with a name and a parent chain, and the
value was entirely in the chain: the console said cmd.exe, and the answer was
the cancelled test run six levels above it. A console is opened here on
purpose, with its own window, and the watcher has to find it and walk up to
this test."""
import os
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import watch

failures = []
log = os.path.join(tempfile.mkdtemp(), "seen.log")


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, wanted {want!r}")


sys.argv = ["watch.py", "6", log]
eye = threading.Thread(target=watch.main, daemon=True)
eye.start()
time.sleep(1)

subprocess.run(["cmd", "/c", "ping -n 2 127.0.0.1"], capture_output=True,
               creationflags=subprocess.CREATE_NEW_CONSOLE)
eye.join(10)

seen = [line for line in open(log, encoding="utf-8") if not line.startswith("---")]
mine = [line for line in seen if "cmd.exe" in line]
check("the console it opened is written down", bool(mine), True)
check("and the chain reaches the process that asked for it",
      any("python.exe" in line for line in mine), True)
check("the nearest name is the window's own owner, not an ancestor",
      (mine[0].split()[2] if mine else "").startswith("cmd.exe("), True)

print(f"3 cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
