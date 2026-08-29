#!/usr/bin/env python3
"""The push judge, which reads the developer's reply instead of the agent's.

It exists to grade the turns the gate let end, so its errors run the opposite
way from the stop judge's. A false PUSH invents a miss and sends someone
hunting a pattern that was never needed. A false NEW hides a real one.

The hard shape is a reply that is short and sharp. "no, 30% not 20%" carries
information the agent could not have had, and reads like a push only because
it is three words long. Length is not the signal; what the reply asks for is.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("push", os.path.join(HERE, "judge_push.py"))
push = importlib.util.module_from_spec(spec)
spec.loader.exec_module(push)

CASES = [
    (True, "I could add the cache or shorten the TTL. Which would you prefer?",
     "dale"),
    (True, "Tests pass and the commit is in. Next I would wire the card.",
     "segui"),
    (True, "Run ./gradlew connectedCheck and tell me what it says.",
     "correlo vos"),
    (True, "That is the plan. Shall I start with the repository layer?",
     "obvio, empeza"),
    (False, "Done, the screener filters by discount now.",
     "no, el corte tiene que ser 30% no 20%"),
    (False, "The retry is in and the suite is green.",
     "ahora armemos el reporte semanal"),
    (False, "I found three anchors that beat the current one.",
     "cual usa el brazo de produccion hoy?"),
    (False, "Which do you want to optimise for, latency or cost?",
     "costo, el presupuesto es 40 dolares por mes"),
    (False, "The build is green and I pushed it.",
     "se rompio en CI, mira el log de la corrida 4471"),
]


def main():
    wrong = []
    for want, closing, reply in CASES:
        got = push.pushed(closing, reply)
        if got is None:
            print("judge unreachable, skipping")
            return 0
        if got != want:
            wrong.append(f"want {'PUSH' if want else 'NEW'} got "
                         f"{'PUSH' if got else 'NEW'} for {reply!r}")
    print(f"{len(CASES) - len(wrong)}/{len(CASES)} correct, {len(wrong)} wrong")
    for line in wrong:
        print("  ", line)
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
