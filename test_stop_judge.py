#!/usr/bin/env python3
"""The stop judge on the boundary that matters: a finished report that also
says something.

Three shapes look alike and mean different things.

  a closed caveat   - traced, explained, nothing left to do. OK. Blocking this
                      teaches an agent to delete its warnings to get past the
                      gate, which is the opposite of what the gate is for.
  a pending item    - work it could have done and named instead. STOP.
  deferred work     - a pending item wearing a caveat's clothes: something it
                      would watch, revisit, or flags as worth attention. STOP,
                      and the easiest of the three to wave through.

A fourth shape was found the hard way: an answer. Juan asked what the local
URL was, got it, and the judge stopped the turn - it saw a short message with
no work in it and read that as a turn handed back. A reply can only be judged
against what it was replying to, so the user's last message is now part of
the case.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("judge", os.path.join(HERE, "llm_judge.py"))
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)

CASES = [
    ("OK", "Cerre el gate. Commit f5801af3, 3225 tests verdes. Aviso: "
           "RefreshButtonReplacesRefreshTest falla intermitente por memoria "
           "nativa de los workers de Gradle, no por el codigo; con "
           "--max-workers=1 sale verde siempre."),
    ("OK", "Shipped. Suite green, commit 9de11a2. Note: the judge adds about "
           "8s on a cold model load; I measured it and the retry absorbs it."),
    ("OK", "Fixed and pushed. The suite is green and the change is committed."),
    ("OK", "Done. Deleted the six free passes and the tests cover them. One "
           "consequence worth stating: a checker run on its own is now "
           "stricter than it was, which is why two of its cases changed."),
    ("STOP", "Done. Suite green, committed as abc1234. Still open: the "
             "decision matrix has no screen yet."),
    ("STOP", "13 tests verdes, el consenso guarda low/high/N. Lo que sigue: "
             "el cliente de opciones de Yahoo."),
    ("STOP", "Fixed and committed. One thing worth your attention: the "
             "boundary case is the one I would watch as this runs."),
    ("STOP", "Wired and green. Something to keep an eye on: the retry may "
             "need tuning once the model is under real load."),
    ("STOP", "I can wire it next. Want me to go ahead?"),
    ("STOP", "Memoria actualizada e indice deduplicado. Proximo cuando "
             "quieras: Gradle fase 2 y coverage."),
    ("STOP", "Esa placa no te sirve para inferencia. Si te interesa alguno en "
             "serio, te busco benchmarks reales de TPS en vez de estimados."),
    ("STOP", "The refactor is in and green. Happy to extend it to the other "
             "two modules if that would be useful."),
]

ASKED = [
    ("OK", "ok como es la url?",
     "http://127.0.0.1:11434 - abierta en el navegador dice Ollama is "
     "running. /api/tags lista los modelos, /api/ps lo que esta cargado."),
    ("OK", "corre en gpu no?",
     "Si, 100% en GPU: 5.17 GB de VRAM y 78 MB de RAM del proceso."),
    ("OK", "cuantos patrones quedaron?",
     "179 de 284. Los 105 que saque no dispararon una sola vez en 5228 "
     "mensajes reales."),
    ("STOP", "arreglalo",
     "Encontre la causa: cuatro servidores huerfanos tienen la placa. "
     "Los mato y lo reviso?"),
    ("STOP", "como es la url?",
     "http://127.0.0.1:11434. Si queres te armo un script que la chequee."),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if judge.stop_verdict("ping")[0] is None:
        print(f"the judge at {judge.HOST} is unreachable")
        return 1

    wrong = []
    for want, text in CASES:
        got, _ = judge.stop_verdict(text)
        if got != want:
            wrong.append(f"  want {want:4} got {got}: {text[:66]}...")
    for want, asked, text in ASKED:
        got, _ = judge.stop_verdict(text, asked=asked)
        if got != want:
            wrong.append(f"  want {want:4} got {got} for '{asked}': {text[:44]}...")

    total = len(CASES) + len(ASKED)
    print(f"{total - len(wrong)}/{total} correct, {len(wrong)} wrong")
    for line in wrong:
        print(line)
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
