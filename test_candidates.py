#!/usr/bin/env python3
"""The proactive question names what the turn left behind, or asks nothing extra.

Its first measured blocks bought no work three times in five, the worst
conversion of any lane. A checklist is easy to wave away; a file name is not.
These come off the turn's own tool calls, so a wrong one is answerable with
evidence rather than with a shrug.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

hints = mod.load("candidates.py")

failures = []


def wrote(*paths):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Edit",
         "input": {"file_path": p}} for p in paths]}}


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, wanted {want!r}")


check("a source file written with no test names the gap",
      any("Thing.kt" in line for line in hints.found(["src/main/a/Thing.kt"])),
      True)
check("a test written alongside it closes that one",
      any("no test" in line for line in
          hints.found(["src/main/a/Thing.kt", "src/test/a/ThingTest.kt"])),
      False)
check("code with no doc touched names the docs",
      any("docs" in line for line in hints.found(["a/Thing.kt", "a/ThingTest.kt"])),
      True)
check("a turn that only wrote docs is not asked for docs",
      hints.found(["README.md"]), [])
check("reading a file is not writing one",
      hints.written({"type": "assistant", "message": {"content": [
          {"type": "tool_use", "id": "t1", "name": "Read",
           "input": {"file_path": "a/Thing.kt"}}]}}), [])
check("a windows path is read the same as any other",
      hints.written(wrote("G:" + chr(92) + "repo" + chr(92) + "a.py")),
      ["G:/repo/a.py"])

print(f"6 cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
