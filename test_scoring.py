#!/usr/bin/env python3
"""Confidence, not just a match.

A pattern matches a word and cannot see around it. "no deja nada pendiente"
trips the pending rule exactly as hard as "queda pendiente", and the hook
blocked a turn over the first one. Widening every pattern until it reads
grammar is a losing game, and sending every hit to the model would be slow and
would put the sure catches at the mercy of one more opinion.

So the list carries confidence. A class written with a trailing ? in
stop-patterns.txt is low: the checker exits MAYBE and the local model decides.
Everything else still condemns on its own. The pairs below are the point of
the whole thing: same weak pattern, opposite meaning, opposite outcome.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)
CASES = [
    (0, "segui", "Una respuesta que no deja nada pendiente se ve igual que un "
                 "informe. Arreglado y commiteado, suite verde."),
    (2, "segui", "Listo, commit abc1234. Queda pendiente conectar la pantalla "
                 "al reporte."),
    (0, "segui", "Sin faltantes: la suite corre entera, commit abc1234."),
    (2, "segui", "Van 12 de 15. Faltan tres tests por escribir."),
    (2, "segui", "Lo dejo asi. Queres que siga con el resto?"),
    (2, "segui", "Listo. Corre la suite y decime si pasa."),
    (0, "segui", "Corre. Suite verde, commit abc1234, la app levanta."),
    (0, "como es la url?", "http://127.0.0.1:11434"),
]


def fire(asked, reply):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8")
    with handle:
        handle.write(json.dumps({"type": "user",
                                 "message": {"content": asked}}) + NL)
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}}) + NL)
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": reply}]}}) + NL)
    state = handle.name + ".state"
    done = subprocess.run(
        [sys.executable, os.path.join(HERE, "check-stop.py")],
        input=json.dumps({"transcript_path": handle.name,
                          "stop_hook_active": False}),
        capture_output=True, text=True,
        env=dict(os.environ, STOP_STATE=state, STOP_LOG=state + ".log"), timeout=150)
    os.unlink(handle.name)
    if os.path.exists(state):
        os.unlink(state)
    return done.returncode


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    failures = []
    for want, asked, reply in CASES:
        got = fire(asked, reply)
        if got != want:
            failures.append(f"  want {want} got {got}: {reply[:60]}...")
    print(f"{len(CASES)} cases, {len(failures)} failures")
    for line in failures:
        print(line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
