#!/usr/bin/env python3
"""Load a sibling hook module once, however many files ask for it.

These files are scripts, not a package, so each one reached for its neighbour
with its own importlib call. Three checkers loaded check-dead-code.py that way
and got three separate module objects: three copies of its state, three copies
of its caches, and the same git command run three times on one stop.

The registry is sys.modules, which is process-wide, so this works even when
two files each carry their own copy of this loader."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PREFIX = "_hook_"


def load(filename, name=None):
    """The module for this file, created once per process."""
    name = name or os.path.basename(filename)[:-3].replace("-", "_")
    key = PREFIX + name
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(
        key, os.path.join(HERE, os.path.basename(filename)))
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        del sys.modules[key]
        raise
    return module
