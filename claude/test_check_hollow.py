#!/usr/bin/env python3
"""Success and emptiness in one message is not a report. It is a warning."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_settle = importlib.util.spec_from_file_location(
    "_hook_settle", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "settle.py"))
settle = importlib.util.module_from_spec(_settle)
_settle.loader.exec_module(settle)

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")


HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-hollow.py")

RUNS = []


def counted():
    """A case counts itself. The total used to be typed in by hand, so
    adding a case left the report claiming the old number - a count
    nobody measured, which is the thing these hooks exist to catch."""
    RUNS.append(None)


def run(message, active=False):
    counted()
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "text", "text": "segui"}]}}) + "\n")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": message}]}}) + "\n")
    handle.close()
    payload = json.dumps({"transcript_path": handle.name, "cwd": HERE,
                          "stop_hook_active": active})
    done = settle.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True)
    os.unlink(handle.name)
    return done.returncode, done.stderr


def main():
    failures = []

    code, err = run("The retry fired live - four lines, two per symbol. Yahoo's options "
                    "endpoint is still returning an empty result, so the move stays "
                    "unpriced; the mechanism that recovers it is now proven.")
    if code != 2:
        failures.append("a proven mechanism with an empty result must fire")
    elif "unpriced" not in err:
        failures.append("the reminder must name the empty half")

    code, _ = run("Anda. El repositorio llama a captureEarningsEvents, pero la tarjeta "
                  "queda vacia porque el endpoint no devuelve nada.")
    if code != 2:
        failures.append("the same shape in Spanish must fire")

    code, _ = run("Corre. La tarjeta imprime 4.2% de descuento sobre 187.30 y el "
                  "repositorio la llama una vez por refresh.")
    if code != 0:
        failures.append("a success with a real value must stay silent")

    code, _ = run("La respuesta viene vacia. Yahoo no devuelve opciones para ese "
                  "simbolo, asi que voy por la fuente de CBOE.")
    if code != 0:
        failures.append("an honest empty report with no success claim must stay silent")

    code, _ = run("BLOCKED: sin clave de FRED la serie queda vacia y el fallback "
                  "tampoco corre. Anda igual.")
    if code == 0:
        failures.append("BLOCKED must not switch this checker off")

    code, err = run("Cerre una forma nueva: el mensaje que dice \"anda\" y a la vez "
                    "\"el precio queda vacio\". El checker nuevo la marca.")
    if code != 0:
        failures.append(f"quoting the shape is not using it: {err[:140]}")

    code, _ = run("Anda y el valor sale. Nada queda vacio.", active=True)
    if code != 0:
        failures.append("stop_hook_active must never re-fire")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
