#!/usr/bin/env python3
"""The floor that keeps a 6.6GB model from landing on a full machine.

Three CLI crashes in one day were all mid-command with a model loading. The
hook is the caller that fires unattended, so it looks first. What this pins is
the shape of the retreat: a skip is not silence. Silence blocks, because a
judge nobody can reach is a judge switched off. A skip lets the turn through,
because the alternative is every session on the box wedged behind memory that
is not coming back.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_live = importlib.util.spec_from_file_location(
    "_hook_live", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "live.py"))
live = importlib.util.module_from_spec(_live)
_live.loader.exec_module(live)

if not live.wanted():
    live.skip()

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

spawn = mod.load("spawn.py")


HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(HERE, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


judge = load("llm_judge.py", "judge")
failures = []
cases = 0


def check(label, got, want):
    global cases
    cases += 1
    if got != want:
        failures.append(f"{label}: got {got!r}, wanted {want!r}")


check("model is pinned, not ambient", judge.MODEL, "qwen3.5:9b")

os.environ["STOP_JUDGE_MODEL"] = "qwen3.5:0.8b"
again = load("llm_judge.py", "judge_again")
check("an env override cannot downgrade it", again.MODEL, "qwen3.5:9b")
os.environ.pop("STOP_JUDGE_MODEL")

judge.FLOOR = 1 << 62
judge._loaded = lambda: False
verdict, seconds = judge.stop_verdict("Listo, suite verde, commit abc1234.")
check("no room and not resident, so it skips", verdict, judge.SKIP)
check("a skip costs nothing", seconds, 0.0)

judge._loaded = lambda: True
verdict, _ = judge.stop_verdict("Listo, suite verde, commit abc1234.")
check("resident, so the floor does not apply", verdict in ("OK", "STOP"), True)

judge.FLOOR = 0
judge._loaded = lambda: False
verdict, _ = judge.stop_verdict("Listo, suite verde, commit abc1234.")
check("room, so the judge runs", verdict in ("OK", "STOP"), True)


def fire(message, floor, host):
    """check-stop.py in its own process, which is the only place the skip
    actually decides anything. The host is pointed at a dead port on purpose:
    with the judge unreachable, the exit code says which of the two retreats
    the hook took."""
    work = [{"type": "tool_use", "id": f"t{n}", "name": "Bash", "input": {}}
            for n in range(6)]
    body = [{"type": "text", "text": message}]
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8")
    with handle:
        handle.write(json.dumps({"type": "user",
                                 "message": {"content": "segui"}}) + NL)
        handle.write(json.dumps({"type": "assistant",
                                 "message": {"content": work}}) + NL)
        handle.write(json.dumps({"type": "assistant",
                                 "message": {"content": body}}) + NL)
    state = handle.name + ".state"
    environment = dict(os.environ, STOP_STATE=state, STOP_LOG=state + ".log",
                       STOP_JUDGE_FLOOR=str(floor), STOP_JUDGE_HOST=host)
    done = spawn.run(
        [sys.executable, os.path.join(HERE, "check-stop.py")],
        input=json.dumps({"transcript_path": handle.name,
                          "stop_hook_active": False}),
        capture_output=True, text=True, env=environment, timeout=120)
    os.unlink(handle.name)
    if os.path.exists(state):
        os.unlink(state)
    return done.returncode


DEAD = "http://127.0.0.1:9"
clean = "Arregle el join y lo commitee. La suite quedo verde."

check("judge unreachable on a machine with room: the hook blocks, because a "
      "judge switched off is the failure this exists to catch",
      fire(clean, 0, DEAD), 2)
check("same judge, no room: the hook lets the turn through instead of wedging "
      "every session on the box",
      fire(clean, 1 << 62, DEAD), 0)

print(f"{cases} cases, {len(failures)} failures")
for line in failures:
    print("  " + line)
sys.exit(1 if failures else 0)
