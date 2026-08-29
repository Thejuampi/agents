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
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")


HERE = os.path.dirname(os.path.abspath(__file__))

settle = mod.load("settle.py")

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

reading = load("judge_reading")
check("a daemon loading a model is late, not gone - starting a second one "
      "against a taken port is what flashed a console over the editor",
      reading.busy(urllib.error.URLError(socket.timeout())), True)
check("a bare timeout reads the same way",
      reading.busy(TimeoutError()), True)
check("refused means nobody is listening, which is the one case worth waking",
      reading.busy(urllib.error.URLError(ConnectionRefusedError(10061, "x"))),
      False)

LIVE = os.environ.get("STOP_TEST_LIVE") == "1"
"""The rest kills the Ollama daemon on this machine and waits for it to come back.

That is a true test of the one recoverable death, and it costs a 5.5GB model
reload and a handful of consoles opening over whatever the developer is
looking at. Paying that on every suite run, while iterating on something else
entirely, buys nothing. It runs when somebody asks for it."""

if not LIVE:
    print(f"{cases} cases, 0 failures"
          " (daemon restart skipped, set STOP_TEST_LIVE=1 to run it)")
    sys.exit(0)


def servers():
    out = spawn.run(["tasklist", "/FI", "IMAGENAME eq llama-server.exe"],
                         capture_output=True, text=True)
    return out.stdout.count("llama-server.exe")


def waitfor(want, seconds=40):
    """Wait for the process count to settle instead of photographing it.

    Ollama answers the verdict before its child is fully up, and it reaps the
    child a moment after the parent dies. Asserting on the instant either side
    of those two events made this test fail once in a suite run and pass three
    times alone, which is worse than having no test at all."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if want(servers()):
            return True
        time.sleep(1)
    return want(servers())


os.environ["STOP_JUDGE_WAKE"] = "20"
judge = load("judge_live")
judge.stop_verdict("Listo, suite verde, commit abc1234.")
check("the model is up before the daemon is killed",
      waitfor(lambda n: n > 0), True)

spawn.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True)
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
code, _ = settle.settled(
    {"transcript_path": handle.name, "stop_hook_active": False},
    dict(os.environ, STOP_STATE=state, STOP_LOG=state + ".log"), timeout=120)
os.unlink(handle.name)
if os.path.exists(state):
    os.unlink(state)

check("a stop with the daemon down still gets a verdict", code, 0)
check("and the daemon is left running for the next session", alive(), True)
check("and no orphan is left holding VRAM for the next load",
      waitfor(lambda n: n <= 1), True)

print(f"{cases} cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
