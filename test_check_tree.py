#!/usr/bin/env python3
"""A failed path with a higher-score sibling still open is leftover."""
import importlib.util
import json
import os
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

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-tree.py")
tree = mod.load("check-tree.py")

RUNS = []


def counted():
    RUNS.append(None)


def run(message, nodes=None, last=None, active=False):
    counted()
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False, encoding="utf-8")
    text = message
    handle.write(json.dumps({"type": "user", "message": {"content": [
        {"type": "text", "text": "segui"}]}}) + "\n")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": text}]}}) + "\n")
    handle.close()
    env = dict(os.environ)
    if nodes is not None:
        store = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"last": last, "nodes": nodes}, store)
        store.close()
        env["STOP_TREE"] = store.name
    payload = json.dumps({"transcript_path": handle.name, "cwd": HERE,
                          "stop_hook_active": active,
                          "last_assistant_message": text})
    done = settle.run([sys.executable, HOOK], input=payload,
                      capture_output=True, text=True, env=env)
    os.unlink(handle.name)
    if nodes is not None:
        os.unlink(env["STOP_TREE"])
    return done.returncode, done.stderr


def pick(nodes, last):
    counted()
    return tree.next_path({"last": last, "nodes": nodes})


def main():
    failures = []

    code, err = run("Regex missed it. Stopping.", nodes=[
        {"id": "regex", "label": "add a leftover pattern", "score": 0.8,
         "status": "failed", "next": ["payload"]},
        {"id": "payload", "label": "read the closing from the payload",
         "score": 0.7, "status": "open", "next": []},
    ], last="regex")
    if code != 2:
        failures.append("a failed path with a high sibling must fire")
    elif "payload" not in err.lower() and "closing" not in err.lower():
        failures.append("the reminder must name the next node")

    node = pick([
        {"id": "a", "score": 0.8, "status": "failed", "next": ["c"]},
        {"id": "b", "label": "high distant", "score": 0.9, "status": "open",
         "next": []},
        {"id": "c", "label": "low neighbour", "score": 0.3, "status": "open",
         "next": ["a"]},
    ], "a")
    if not node or node.get("id") != "b":
        failures.append("a low neighbour waits while a higher node is open")

    node = pick([
        {"id": "a", "score": 0.8, "status": "failed", "next": ["b"]},
        {"id": "b", "label": "near", "score": 0.72, "status": "open",
         "next": ["a"]},
        {"id": "c", "label": "far", "score": 0.8, "status": "open", "next": []},
    ], "a")
    if not node or node.get("id") != "b":
        failures.append("among high nodes the neighbour of last comes first")

    node = pick([
        {"id": "a", "score": 0.8, "status": "failed", "next": ["b"]},
        {"id": "b", "label": "only neighbour", "score": 0.3, "status": "open",
         "next": ["a"]},
    ], "a")
    if not node or node.get("id") != "b":
        failures.append("after a miss the next path is taken even when low")

    node = pick([
        {"id": "a", "score": 0.8, "status": "taken", "next": []},
        {"id": "b", "label": "unused alt", "score": 0.7, "status": "open",
         "next": []},
    ], "a")
    if node is not None:
        failures.append("a success leaves unconnected alternatives alone")

    node = pick([
        {"id": "a", "score": 0.8, "status": "taken", "next": ["b"]},
        {"id": "b", "label": "related next", "score": 0.7, "status": "open",
         "next": ["a"]},
    ], "a")
    if not node or node.get("id") != "b":
        failures.append("related work next to a finished path is still work")

    node = pick([
        {"id": "a", "score": 8, "status": "failed", "next": ["b"]},
        {"id": "b", "label": "tenths", "score": 7, "status": "open", "next": []},
    ], "a")
    if not node or abs(tree.score_of(node) - 0.7) > 0.01:
        failures.append("a score written as 7 of 10 is 0.7")

    code, _ = run("Done. Suite green.", nodes=[
        {"id": "a", "score": 0.8, "status": "taken", "next": []},
        {"id": "b", "score": 0.2, "status": "skipped", "next": []},
    ], last="a")
    if code != 0:
        failures.append("a finished tree must stay silent")

    code, err = run("The regex missed it. Two other approaches remain.")
    if code != 2:
        failures.append("named leftover paths without a tree file must fire")
    elif "PATH YOU DID NOT TAKE" not in err:
        failures.append("named leftover must say the path was not taken")

    code, _ = run("quedan caminos por probar")
    if code != 2:
        failures.append("Spanish leftover on the tree must fire")

    code, _ = run("The regex missed it. I could also try a rewrite.")
    if code != 2:
        failures.append("a leftover could-also-try must fire")

    code, _ = run("The report quotes `could also try a rewrite`.")
    if code != 0:
        failures.append("a quoted leftover phrase must stay silent")

    code, _ = run("Regex missed it.", nodes=[
        {"id": "regex", "score": 0.8, "status": "failed", "next": ["payload"]},
        {"id": "payload", "score": 0.7, "status": "open", "next": []},
    ], last="regex", active=True)
    if code != 0:
        failures.append("stop_hook_active must stand down")

    code, _ = run("Fixed and pushed. The build passes on CI.")
    if code != 0:
        failures.append("a clean delivery must stay silent")

    counted()
    root = tempfile.mkdtemp()
    os.mkdir(os.path.join(root, ".grok"))
    with open(os.path.join(root, ".grok", "decisions.json"), "w", encoding="utf-8") as store:
        json.dump({"last": "a", "nodes": [
            {"id": "a", "score": 0.8, "status": "failed", "next": ["b"]},
            {"id": "b", "label": "from disk", "score": 0.7, "status": "open", "next": []},
        ]}, store)
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Regex missed it. Stopping."}]}}) + chr(10))
    handle.close()
    env = dict(os.environ)
    env.pop("STOP_TREE", None)
    payload = json.dumps({"transcript_path": handle.name, "cwd": root,
                          "stop_hook_active": False,
                          "last_assistant_message": "Regex missed it. Stopping."})
    done = settle.run([sys.executable, HOOK], input=payload,
                      capture_output=True, text=True, env=env)
    os.unlink(handle.name)
    if done.returncode != 2 or "from disk" not in done.stderr:
        failures.append("the checker must read cwd .grok/decisions.json")

    counted()
    cwd_root = tempfile.mkdtemp()
    os.mkdir(os.path.join(cwd_root, ".grok"))
    with open(os.path.join(cwd_root, ".grok", "decisions.json"), "w", encoding="utf-8") as store:
        json.dump({"last": "a", "nodes": [
            {"id": "a", "score": 0.8, "status": "failed", "next": ["b"]},
            {"id": "b", "label": "from cwd", "score": 0.9, "status": "open", "next": []},
        ]}, store)
    session = tempfile.mkdtemp()
    with open(os.path.join(session, "decisions.json"), "w", encoding="utf-8") as store:
        json.dump({"last": "a", "nodes": [
            {"id": "a", "score": 0.8, "status": "failed", "next": ["c"]},
            {"id": "c", "label": "from session", "score": 0.6, "status": "open", "next": []},
        ]}, store)
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8", dir=session)
    handle.write(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Regex missed it. Stopping."}]}}) + chr(10))
    handle.close()
    env = dict(os.environ)
    env.pop("STOP_TREE", None)
    payload = json.dumps({"transcript_path": handle.name, "cwd": cwd_root,
                          "stop_hook_active": False,
                          "last_assistant_message": "Regex missed it. Stopping."})
    done = settle.run([sys.executable, HOOK], input=payload,
                      capture_output=True, text=True, env=env)
    os.unlink(handle.name)
    if done.returncode != 2 or "from session" not in done.stderr:
        failures.append("the session tree wins over cwd")
    elif "from cwd" in done.stderr:
        failures.append("cwd must not win when a session tree exists")

    print(f"{len(RUNS)} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
