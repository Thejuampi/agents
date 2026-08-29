#!/usr/bin/env python3
"""Builds throwaway repos and checks the hook only fires on hollow done claims."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-done-claim.py")

RUNS = []


def counted():
    """A case counts itself. The total used to be typed in by hand, so
    adding a case left the report claiming the old number - a count
    nobody measured, which is the thing these hooks exist to catch."""
    RUNS.append(None)

REAL = ("El tope de costo quedo cerrado y cableado hasta la tarjeta. "
        "Suite completa: exit 0, 0 fallas. PRD actualizado.")


def repo():
    root = tempfile.mkdtemp()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git"] + args, cwd=root, capture_output=True)
    open(os.path.join(root, "seed.txt"), "w").write("seed\n")
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, capture_output=True)
    return root


def transcript(root, message, files, ran):
    blocks = []
    for path in files:
        blocks.append({"type": "tool_use", "name": "Write",
                       "input": {"file_path": os.path.join(root, path)}})
    for command in ran:
        blocks.append({"type": "tool_use", "name": "Bash", "input": {"command": command}})
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write(json.dumps({"type": "assistant", "message": {"content": blocks}}) + "\n")
    handle.write(json.dumps({"type": "assistant", "message": {
        "content": [{"type": "text", "text": message}]}}) + "\n")
    handle.close()
    return handle.name


def run(root, message, files=(), ran=(), active=False):
    counted()
    for path in files:
        full = os.path.join(root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w").write("class Thing\n")
    path = transcript(root, message, files, ran)
    payload = json.dumps({"transcript_path": path, "cwd": root, "stop_hook_active": active})
    done = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    os.unlink(path)
    return done.returncode, done.stderr


def main():
    failures = []

    code, err = run(repo(), REAL, files=["src/Hedge.kt"], ran=["./gradlew :core:test"])
    if code != 2:
        failures.append("hollow done claim did not fire")
    else:
        for want in ("build never ran", "live endpoint", "uncommitted"):
            if want not in err:
                failures.append(f"missing gap line: {want}")

    root = repo()
    open(os.path.join(root, "Hedge.kt"), "w").write("class Thing\n")
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "w"], cwd=root, capture_output=True)
    code, err = run(root, REAL, files=["Hedge.kt"],
                    ran=["./gradlew assembleDebug", "adb install app.apk"])
    if code != 0:
        failures.append(f"built, ran and committed must stay silent: {err[:120]}")

    code, _ = run(repo(), "Que preferis, A o B?", files=["src/Hedge.kt"])
    if code != 0:
        failures.append("no completion claim must stay silent")

    code, _ = run(repo(), REAL, files=[])
    if code != 0:
        failures.append("no source written must stay silent")

    code, _ = run(repo(), REAL, files=["src/Hedge.kt"], ran=["./gradlew test"], active=True)
    if code != 0:
        failures.append("stop_hook_active must never re-fire")

    code, _ = run(repo(), "BLOCKED: no device is attached, the app cannot run here.",
                  files=["src/Hedge.kt"])
    if code != 0:
        failures.append("BLOCKED must pass through")

    code, _ = run(repo(), REAL, files=["src/test/HedgeTest.kt"], ran=["./gradlew test"])
    if code != 0:
        failures.append("test-only work must stay silent")

    root = repo()
    outside = os.path.join(tempfile.mkdtemp(), "tool.py")
    open(outside, "w").write("x = 1\n")
    path = transcript(root, REAL, [], ["python tool.py"])
    lines = open(path, encoding="utf-8").read().splitlines()
    blocks = [{"type": "tool_use", "name": "Write", "input": {"file_path": outside}},
              {"type": "tool_use", "name": "Bash", "input": {"command": "python tool.py"}}]
    open(path, "w", encoding="utf-8").write(
        json.dumps({"type": "assistant", "message": {"content": blocks}}) + "\n"
        + lines[-1] + "\n")
    counted()
    payload = json.dumps({"transcript_path": path, "cwd": root, "stop_hook_active": False})
    done = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
    os.unlink(path)
    if done.returncode != 0:
        failures.append(f"source outside the repo is not this repo deliverable: {done.stderr[:120]}")

    root = repo()
    code, err = run(root, REAL, files=["src/Hedge.kt"],
                    ran=["./gradlew assembleDebug",
                         "python /tmp/blk.py",
                         "curl -s https://query1.finance.yahoo.com/v7/finance/options/AAPL"])
    if code != 2:
        failures.append("a scratch script and a fixture fetch are not running the app")
    elif "live endpoint" not in err:
        failures.append("the run gap must be reported for scratch plumbing")

    root = repo()
    open(os.path.join(root, "Hedge.kt"), "w").write("class Thing\n")
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "w"], cwd=root, capture_output=True)
    code, err = run(root, REAL, files=["Hedge.kt"],
                    ran=["./gradlew assembleDebug", "curl -s http://localhost:8080/health"])
    if code != 0:
        failures.append(f"a call to your own running service counts: {err[:120]}")

    root = repo()
    open(os.path.join(root, "Hedge.kt"), "w").write("class Thing\n")
    open(os.path.join(root, "smoke.py"), "w").write("print(1)\n")
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "w"], cwd=root, capture_output=True)
    code, err = run(root, REAL, files=["Hedge.kt"],
                    ran=["./gradlew assembleDebug", "python smoke.py"])
    if code != 0:
        failures.append(f"a script inside the repo counts: {err[:120]}")

    root = repo()
    open(os.path.join(root, "Hedge.kt"), "w").write("class Thing\n")
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "w"], cwd=root, capture_output=True)
    code, err = run(root, REAL, files=["Hedge.kt"],
                    ran=["./gradlew assembleDebug",
                         'curl -s -b /tmp/yc.txt -A "$UA" '
                         '"https://query2.finance.yahoo.com/v7/finance/options/LVS"'])
    if code != 0:
        failures.append(f"a real host answering is a live endpoint: {err[:160]}")

    code, err = run(repo(), REAL, files=["src/Hedge.kt"],
                    ran=["./gradlew assembleDebug",
                         "curl -s https://query2.finance.yahoo.com/v7/finance/options/LVS "
                         "-o core/src/test/resources/yahoo/options/LVS.json"])
    if code != 2:
        failures.append("a download straight into test resources only refills fixtures")
    elif "live endpoint" not in err:
        failures.append("the run gap must be reported for a fixture refill")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
