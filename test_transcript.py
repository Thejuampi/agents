#!/usr/bin/env python3
"""Who spoke, what they said, and what the agent answered them.

Every reader of a transcript in this directory depends on these three, and
each defect they ever had was the same one: the gate's own wake arrives wearing
the user's role. The exchange reader is the newest of them and the easiest to
get wrong, because the answer to a request is not the next thing the agent
says - it is the last thing it says before the developer speaks again.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

reader = mod.load("transcript.py")

failures = []


def user(text):
    return {"type": "user", "message": {"content": text}}


def agent(text):
    return {"type": "assistant", "message": {"content": [
        {"type": "text", "text": text}]}}


def tool():
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}}


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, wanted {want!r}")


WAKE = user("Stop hook feedback:" + chr(10) + "KEEP GOING - work left")

talk = [user("arregla el join"), tool(), agent("Voy por el segundo caso."),
        agent("Listo, verde."), WAKE, agent("Agregue el test que faltaba."),
        user("y ahora el reporte"), tool(), agent("Hecho, corre.")]

pairs = reader.exchanges(talk)
check("one pair per developer turn, the gate's wake is not one",
      len(pairs), 2)
check("the answer is the last word before the developer spoke again",
      pairs[0], ("arregla el join", "Agregue el test que faltaba."))
check("and the newest pair is last",
      pairs[1], ("y ahora el reporte", "Hecho, corre."))
check("the window keeps the most recent turns",
      reader.exchanges(talk, 1), [("y ahora el reporte", "Hecho, corre.")])

noise = [user("[Image: 1200x800]"), agent("Veo la captura."),
         user("Request interrupted by user"), agent("Paro.")]
check("a screenshot and an interrupt are not the developer speaking",
      reader.exchanges(noise), [])

check("a turn with no answer yet still counts as asked",
      reader.exchanges([user("dale")]), [("dale", "")])

check("the last developer line is the newest real ask",
      reader.last_user(talk), "y ahora el reporte")
check("a wake is not the last ask",
      reader.last_user([user("arregla el join"), WAKE]), "arregla el join")

print(f"8 cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
