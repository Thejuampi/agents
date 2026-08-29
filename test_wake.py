#!/usr/bin/env python3
"""The daemon starting itself, which is the only recoverable way the judge dies.

An unreachable judge blocks every stop on the machine, and that stays true. The
question here is narrower: when the reason is simply that nobody launched
Ollama, does the hook fix it without a human? Two of these cases are guards -
somebody else's server, and the start switched off - and the last one kills the
daemon for real and asks the hook to bring it back.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)
failures = []
cases = 0


def load(alias):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, "llm_judge.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(label, got, want):
    global cases
    cases += 1
    if got != want:
        failures.append(f"{label}: got {got!r}, wanted {want!r}")


def alive():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2):
            return True
    except Exception:
        return False


os.environ["STOP_JUDGE_HOST"] = "http://127.0.0.1:9"
elsewhere = load("judge_elsewhere")
check("somebody else's server is not ours to start", elsewhere._wake(), False)
os.environ.pop("STOP_JUDGE_HOST")

os.environ["STOP_JUDGE_WAKE"] = "0"
off = load("judge_off")
check("zero turns the start off", off._wake(), False)
os.environ.pop("STOP_JUDGE_WAKE")

def servers():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq llama-server.exe"],
                         capture_output=True, text=True)
    return out.stdout.count("llama-server.exe")


judge = load("judge_live")
judge.stop_verdict("Listo, suite verde, commit abc1234.")
check("the model is up before the daemon is killed", servers() > 0, True)

subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True)
check("killing the parent hard leaves the model server orphaned, holding the "
      "card - this is what made the judge answer SKIP for an hour",
      servers() > 0, True)
for _ in range(15):
    if not alive():
        break
    time.sleep(1)
check("the daemon is really down before the hook is asked", alive(), False)

work = [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]
body = [{"type": "text", "text": "Arregle el join y lo commitee. La suite quedo verde."}]
handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
with handle:
    handle.write(json.dumps({"type": "user", "message": {"content": "segui"}}) + NL)
    handle.write(json.dumps({"type": "assistant", "message": {"content": work}}) + NL)
    handle.write(json.dumps({"type": "assistant", "message": {"content": body}}) + NL)
state = handle.name + ".state"
done = subprocess.run(
    [sys.executable, os.path.join(HERE, "check-stop.py")],
    input=json.dumps({"transcript_path": handle.name, "stop_hook_active": False}),
    capture_output=True, text=True, env=dict(os.environ, STOP_STATE=state),
    timeout=120)
os.unlink(handle.name)
if os.path.exists(state):
    os.unlink(state)

check("a stop with the daemon down still gets a verdict", done.returncode, 0)
check("and the daemon is left running for the next session", alive(), True)
check("and no orphan is left holding VRAM for the next load", servers() <= 1, True)

print(f"{cases} cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
