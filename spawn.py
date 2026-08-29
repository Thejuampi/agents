#!/usr/bin/env python3
"""Child processes that do not steal the screen.

On Windows a console program started from a console-less parent gets a console
of its own, and it flashes on top of whatever the developer is looking at. The
gate runs every checker as its own process on every turn, so a single stop was
a burst of windows opening and closing over the editor.

CREATE_NO_WINDOW says the child needs no console. It exists only on Windows,
and passing it anywhere else is an error, so the flag is resolved once here
and every spawn in this directory goes through these two calls."""
import os
import subprocess
import sys

WINDOWS = sys.platform == "win32"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if WINDOWS else 0
DETACHED = ((getattr(subprocess, "DETACHED_PROCESS", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
             | NO_WINDOW) if WINDOWS else 0)


LEDGER = "STOP_SPAWN_LOG"
"""Set it to a path and every child started here is written down.

Process count is the thing to keep honest, so it has to be answerable at any
moment rather than reasoned about."""


def _note(command):
    path = os.environ.get(LEDGER)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(" ".join(str(part) for part in command[:4]) + "\n")
    except OSError:
        pass


def _flagged(kw, flags):
    if WINDOWS:
        kw["creationflags"] = kw.get("creationflags", 0) | flags
    return kw


def run(command, **kw):
    """subprocess.run, with no console for the child."""
    _note(command)
    return subprocess.run(command, **_flagged(kw, NO_WINDOW))


def detached(command, **kw):
    """A daemon that outlives this process and shows nothing."""
    _note(command)
    return subprocess.Popen(command, **_flagged(kw, DETACHED))
