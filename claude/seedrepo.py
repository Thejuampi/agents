#!/usr/bin/env python3
"""A git repository for a test, built once and copied after that.

Every case used to build its own: five git commands each, and on Windows each
one can flash a console. One seed per process and a directory copy per case
costs the same five, once."""
import importlib.util
import os
import shutil
import tempfile

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")

SEED = []


def _build():
    root = tempfile.mkdtemp()
    for args in (["init", "-q"],
                 ["config", "user.email", "t@t"],
                 ["config", "user.name", "t"]):
        spawn.run(["git"] + args, cwd=root, capture_output=True)
    with open(os.path.join(root, "seed.txt"), "w") as handle:
        handle.write("seed\n")
    spawn.run(["git", "add", "-A"], cwd=root, capture_output=True)
    spawn.run(["git", "commit", "-qm", "seed"],
              cwd=root, capture_output=True)
    return root


def seeded(files=None):
    """A fresh work tree with one commit behind it."""
    if not SEED or not os.path.isdir(SEED[0]):
        SEED[:] = [_build()]
    clone = tempfile.mkdtemp()
    shutil.rmtree(clone)
    shutil.copytree(SEED[0], clone)
    for name, body in (files or {}).items():
        path = os.path.join(clone, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
    return clone
