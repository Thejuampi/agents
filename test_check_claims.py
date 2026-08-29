#!/usr/bin/env python3
"""Claims about files and symbols are checked against a real tree."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-claims.py")
NL = chr(10)

RUNS = []


def counted():
    """A case counts itself. The total used to be typed in by hand, so
    adding a case left the report claiming the old number - a count
    nobody measured, which is the thing these hooks exist to catch."""
    RUNS.append(None)


def repo(files=()):
    root = tempfile.mkdtemp()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git"] + args, cwd=root, capture_output=True)
    for path, body in files:
        full = os.path.join(root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(body)
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, capture_output=True)
    return root


def run(root, message):
    counted()
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": message}]}}) + "\n")
    handle.close()
    payload = json.dumps({"transcript_path": handle.name, "cwd": root, "stop_hook_active": False})
    done = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    os.unlink(handle.name)
    return done.returncode, done.stderr


def main():
    failures = []
    tree = repo([("src/EventMove.kt", "fun splitEvent() = 1\n"),
                 ("src/Hedge.kt", "fun parseConsensus() = 2\n")])

    code, err = run(tree, "Agregue `Ghost.kt` para separar el evento.")
    if code != 2:
        failures.append("a file claimed as added but absent must fire")
    elif "Ghost.kt" not in err:
        failures.append("the reminder must name the missing file")

    code, err = run(tree, "`parseConsensus` era un wrapper que solo usaban los tests. Borrado.")
    if code != 2:
        failures.append("a symbol claimed as deleted but still declared must fire")

    code, _ = run(tree, "Agregue `EventMove.kt` para separar el evento antes de dividir.")
    if code != 0:
        failures.append("a file that is really there must stay silent")

    code, _ = run(tree, "El ratio se lee contra el evento, ver `splitEvent`.")
    if code != 0:
        failures.append("a plain mention with no claim must stay silent")

    code, _ = run(tree, "Anda. 2090 tests, 0 fallos, la tarjeta imprime una vez.")
    if code != 0:
        failures.append("a report with no file claims must stay silent")

    code, _ = run(tree, "BLOCKED: no puedo borrar `parseConsensus`, falta el SDK.")
    if code != 0:
        failures.append("a blocker that claims nothing has nothing to check")

    code, _ = run(tree, "BLOCKED: falta el SDK para la suite. "
                        "`parseConsensus` era un wrapper y quedo borrado.")
    if code != 2:
        failures.append("BLOCKED must not launder a claim the tree refutes")

    other = repo([("hooks/llm_judge.py", "def wake(): return 1" + NL)])
    counted()
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Edit", "input": {
            "file_path": os.path.join(other, "hooks", "llm_judge.py")}}]}}) + NL)
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Agregue `llm_judge.py` para despertar el daemon."}]}}) + NL)
    handle.close()
    payload = json.dumps({"transcript_path": handle.name, "cwd": tree,
                          "stop_hook_active": False})
    done = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    os.unlink(handle.name)
    if done.returncode != 0:
        failures.append(f"a file written outside the session repo is still in a tree: {done.stderr[:160]}")

    counted()
    payload = json.dumps({"transcript_path": HOOK, "cwd": tree, "stop_hook_active": True})
    done = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    if done.returncode != 0:
        failures.append("stop_hook_active must never re-fire")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
