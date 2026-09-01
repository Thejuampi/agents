#!/usr/bin/env python3
"""A real blocker passes. A declared one does not."""
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
HOOK = os.path.join(HERE, "check-blocked.py")

RUNS = []


def counted():
    """A case counts itself. The total used to be typed in by hand, so
    adding a case left the report claiming the old number - a count
    nobody measured, which is the thing these hooks exist to catch."""
    RUNS.append(None)

REAL = ("BLOCKED: no device is attached. adb devices lists nothing and the "
        "emulator refuses to boot with HAXM off.")


def transcript(messages, acted=True):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "text", "text": "hace el trabajo"}]}}) + "\n")
    if acted:
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "adb devices"}}]}}) + "\n")
    for text in messages:
        handle.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": text}]}}) + "\n")
    handle.close()
    return handle.name


def fire(path, active=False):
    counted()
    payload = json.dumps({"transcript_path": path, "cwd": HERE, "stop_hook_active": active})
    done = settle.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True)
    return done.returncode, done.stderr


def run(messages, acted=True):
    path = transcript(messages, acted)
    code, err = fire(path)
    os.unlink(path)
    return code, err


def main():
    failures = []

    code, err = run([REAL])
    if code != 0:
        failures.append(f"a blocker reached by trying must pass: {err[:120]}")

    code, err = run([REAL], acted=False)
    if code != 2:
        failures.append("a blocker declared with nothing run must fire")
    elif "walked into" not in err:
        failures.append("the reminder must name the missing attempt")

    code, err = run(["BLOCKED: falta el SDK. Tambien falta la clave de FRED. "
                     "Y el emulador no arranca. Ademas el PRD no define el corte."])
    if code != 2:
        failures.append("a list of blockers must fire")
    elif "more than one thing" not in err:
        failures.append("the reminder must name the list")

    code, err = run([REAL, REAL, REAL])
    if code != 2:
        failures.append("three blocked closings in a row must fire")
    elif "in a row" not in err:
        failures.append("the reminder must name the streak")

    code, _ = run(["Anda. La tarjeta imprime una vez y el repositorio la llama."])
    if code != 0:
        failures.append("a message with no blocker must stay silent")

    code, err = run(["Cerre la evasion mas barata que quedaba: `BLOCKED:`. Todos los "
                     "checkers dejaban pasar cualquier mensaje que la contuviera. "
                     "Ahora la audita con tres preguntas.\n\n"
                     "El bloqueante genuino pasa limpio. Suites verdes."], acted=False)
    if code != 0:
        failures.append(f"quoting the escape is not using it: {err[:160]}")

    code, _ = run(["Corre. El commit quedo en la rama.", REAL])
    if code != 0:
        failures.append("one blocker after real work must pass")

    path = transcript([REAL], acted=False)
    code, _ = fire(path, active=True)
    os.unlink(path)
    if code != 0:
        failures.append("stop_hook_active must never re-fire")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
