#!/usr/bin/env python3
"""Every checker must tell using a phrase from saying it.

This system describes itself. A report about the detector quotes the words the
detector hunts, so a checker that reads raw text fires on the prose explaining
it. Three checkers shipped that bug one after another, each found only when it
blocked a real turn.

So the rule gets a test instead of a memory: feed every check-*.py a closing
message that quotes the whole trigger vocabulary inside backticks, fences and
quotation marks, and require silence. A checker that objects here reads text
it was never meant to own.
"""
import importlib.util
import glob
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


sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {"check-stop.py"}

QUOTING = """Cerre la evasion mas barata del sistema. Los patrones nuevos son
`ask: should i`, `announce: lo que sigue`, `handoff: you can merge it` y
`wait: held pending`. La marca de escape es `BLOCKED:` y ahora se audita.

Juan escribio "decime y lo cableo de punta a punta" y esa frase dispara el hook.
El otro agente cerro con "Lo que sigue: cablear el PreReport" y con
"Still open: the decision matrix has no screen. That's the next build."

El reporte decia "2118 tests, 0 failures, 19 skipped" y la corrida cerro en verde.

```
Voy por el commit en rama. Falta correr assembleDebug.
Deberias correr /context y avisarme que da.
```

Todo eso queda citado, no dicho. El detector corre sobre los ocho suites."""


def transcript(message):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "text", "text": "segui"}]}}) + "\n")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "python run-tests.sh"}}]}}) + "\n")
    handle.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": [
            {"type": "text", "text": "8 cases, 0 failures"}]}]}}) + "\n")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": message}]}}) + "\n")
    handle.close()
    return handle.name


def main():
    path = transcript(QUOTING)
    payload = json.dumps({"transcript_path": path, "cwd": HERE, "stop_hook_active": False})

    checkers = [p for p in sorted(glob.glob(os.path.join(HERE, "check-*.py")))
                if os.path.basename(p) not in SKIP]
    failures = []
    for checker in checkers:
        done = settle.run([sys.executable, checker], input=payload,
                              capture_output=True, text=True)
        if done.returncode != 0:
            first = (done.stderr.strip().splitlines() or [""])[0]
            failures.append(f"{os.path.basename(checker)} fired on quoted text: {first}")
    os.unlink(path)

    print(f"{len(checkers)} checkers, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
