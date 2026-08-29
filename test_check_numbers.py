#!/usr/bin/env python3
"""A number in a report must have been printed by something in the session."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-numbers.py")

RUNS = []


def counted():
    """A case counts itself. The total used to be typed in by hand, so
    adding a case left the report claiming the old number - a count
    nobody measured, which is the thing these hooks exist to catch."""
    RUNS.append(None)


def run(message, outputs=(), said_to_me=()):
    """outputs are tool results; said_to_me is what the user or a peer session
    put in the conversation. Both are things the agent did not write."""
    counted()
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for text in outputs:
        handle.write(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "content": text}]}}) + "\n")
    for text in said_to_me:
        handle.write(json.dumps({"type": "user",
                                 "message": {"role": "user", "content": text}}) + "\n")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": message}]}}) + "\n")
    handle.close()
    payload = json.dumps({"transcript_path": handle.name, "stop_hook_active": False})
    done = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    os.unlink(handle.name)
    return done.returncode, done.stderr


def main():
    failures = []

    code, err = run("Suite completa: exit 0, 2236 pruebas, 0 fallas.",
                    ["Binary file /tmp/f3.log matches", "exit=0"])
    if code != 2:
        failures.append("an unprinted test count must fire")
    elif "2236" not in err:
        failures.append("the reminder must name the invented number")

    code, _ = run("Suite completa: 2236 pruebas, 0 fallas.",
                  ["2236 tests completed, 0 failed", "BUILD SUCCESSFUL"])
    if code != 0:
        failures.append("a number the session printed must stay silent")

    code, err = run("El peer cerro el gate y reporto 3225 tests verdes.",
                    said_to_me=["Commit f5801af3. 3225 tests verdes."])
    if code != 0:
        failures.append(f"a number a peer reported is quoted, not invented: {err[:120]}")

    code, _ = run("Los 41 fallos que pegaste vienen del worker sin memoria.",
                  said_to_me=["mira esto: 41 failures en el ultimo build"])
    if code != 0:
        failures.append("a number the user typed must stay silent")

    code, _ = run("La suite quedo en 4711 tests verdes.",
                  said_to_me=["y como venimos con los tests?"])
    if code != 2:
        failures.append("a number nobody printed still fires")

    code, _ = run("Anda. El pre-reporte se escribe en cada refresh.", ["BUILD SUCCESSFUL"])
    if code != 0:
        failures.append("a report with no numbers must stay silent")

    code, _ = run("1276 tests, 0 fallos, 16 skipped.",
                  ["1,276 tests completed", "0 failures", "16 skipped"])
    if code != 0:
        failures.append("a thousands separator must not count as a different number")

    code, _ = run("BLOCKED: no puedo correr la suite sin el SDK. 999 pruebas quedan sin medir.",
                  ["nothing"])
    if code == 0:
        failures.append("BLOCKED must not launder an unmeasured number")

    code, err = run('El otro agente cerro con "3312 tests, 0 failures" y el log decia\n'
                    "```\n7777 tests completed\n```\n"
                    "Ninguno de esos numeros es mio.",
                    ["BUILD SUCCESSFUL"])
    if code != 0:
        failures.append(f"a number quoted from someone else is not a claim: {err[:120]}")

    code, err = run("La suite dio `4141 tests, 0 failures` y cerro en verde.",
                    ["BUILD SUCCESSFUL"])
    if code != 2:
        failures.append("backticks are formatting, not attribution: a figure in "
                        "them is still measured or invented")
    elif "4141" not in err:
        failures.append("the reminder must name the backticked number")

    counted()
    payload = json.dumps({"transcript_path": HOOK, "stop_hook_active": True})
    done = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    if done.returncode != 0:
        failures.append("stop_hook_active must never re-fire")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
