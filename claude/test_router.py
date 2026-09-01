#!/usr/bin/env python3
import json
import os
import tempfile
import unittest

import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

settle = mod.load("settle.py")
gate = mod.load("check-stop.py")


def transcript(path, turns):
    with open(path, "w", encoding="utf-8") as handle:
        for kind, payload in turns:
            if kind == "user":
                entry = {"type": "user", "message": {"role": "user",
                                                     "content": payload}}
            elif kind == "say":
                entry = {"type": "assistant",
                         "message": {"content": [
                             {"type": "text", "text": payload}]}}
            else:
                entry = {"type": "assistant",
                         "message": {"content": [
                             {"type": "tool_use", "name": payload,
                              "id": kind, "input": {}}]}}
            handle.write(json.dumps(entry) + "\n")


class Router(unittest.TestCase):
    def setUp(self):
        self.room = tempfile.mkdtemp(prefix="router-")
        self.repo = os.path.join(self.room, "repo")
        os.makedirs(self.repo)
        with open(os.path.join(self.repo, "README.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("# repo\n")

    def fire(self, turns, extra=None, name="t.jsonl"):
        path = os.path.join(self.room, name)
        transcript(path, turns)
        payload = {"transcript_path": path, "cwd": self.repo,
                   "stop_hook_active": False}
        env = dict(os.environ,
                   STOP_STATE=os.path.join(self.room, "state.json"),
                   STOP_LOG=os.path.join(self.room, "state.log"),
                   STOP_HOLDOUT="0")
        if extra:
            env.update(extra)
        return settle.once(payload, env)

    def logged(self):
        path = os.path.join(self.room, "state.log")
        if not os.path.exists(path):
            return ""
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_short_announce_still_blocks(self):
        _, out = self.fire([
            ("user", "go"),
            ("t1", "Read"),
            ("say", "Next steps: wire the HTTP client."),
        ])
        self.assertIn("YOU ALREADY HAVE PERMISSION", out)

    def test_long_announce_still_blocks(self):
        body = ("Next steps: wire the HTTP client. "
                "The helper keeps the contract the caller already had. ") * 6
        _, out = self.fire([
            ("user", "go"),
            ("t1", "Read"),
            ("t2", "Read"),
            ("t3", "Read"),
            ("say", body),
        ])
        self.assertIn("YOU ALREADY HAVE PERMISSION", out)

    def test_long_turn_still_asks_the_judge(self):
        seen = []

        def fake(message, asked=None, before=None):
            seen.append(message)
            return "OK", 0.0

        old = gate.judge.stop_verdict
        gate.judge.stop_verdict = fake
        body = (
            "The helper now returns the same payload the caller already used. "
            "Names stay as they were so the rest of the module keeps compiling. "
            "The log matches the run I just did. The edit is on the branch "
            "the session already had. I left the names as they were. "
            "The existing caller keeps its contract. The payload shape is "
            "the same one the tests already cover. Nothing else moved. "
            "The caller and the helper agree on the types they already had."
        )
        try:
            self.fire([
                ("user", "go"),
                ("t1", "Read"),
                ("t2", "Read"),
                ("t3", "Read"),
                ("say", body),
            ])
        finally:
            gate.judge.stop_verdict = old
        self.assertTrue(seen)

    def test_holdout_releases_a_question(self):
        code, _ = self.fire([
            ("user", "go"),
            ("t1", "Read"),
            ("say", "Should I wire it up now?"),
        ], extra={"STOP_HOLDOUT": "1"})
        self.assertEqual(0, code)

    def test_blocked_claim_ignores_holdout(self):
        _, out = self.fire([
            ("user", "go"),
            ("t1", "Read"),
            ("say", "BLOCKED: I need you to tell me which approach you prefer."),
        ], extra={"STOP_HOLDOUT": "1"})
        self.assertIn("NOT A PASSWORD", out)

    def test_busy_leftover_with_cuando_quieras_blocks(self):
        body = (
            "El disco estaba sano. Ollama volvio. Tests verdes. "
            "Paper 25 paginas. "
        ) * 8 + (
            "Lo que queda de extra-FN. "
            "Siguiente experimento cuando quieras."
        )
        _, out = self.fire([
            ("user", "go"),
            ("t1", "Read"),
            ("t2", "Read"),
            ("t3", "Read"),
            ("say", body),
        ])
        self.assertIn("YOU ALREADY HAVE PERMISSION", out)

    def test_four_hour_turn_skips_the_judge(self):
        from datetime import datetime, timedelta, timezone
        start = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        body = (
            "The helper now returns the same payload the caller already used. "
            "Names stay as they were so the rest of the module keeps compiling. "
            "The log matches the run I just did. The edit is on the branch "
            "the session already had. I left the names as they were. "
            "The existing caller keeps its contract. The payload shape is "
            "the same one the tests already cover. Nothing else moved. "
            "The caller and the helper agree on the types they already had."
        )
        path = os.path.join(self.room, "four.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "type": "user", "timestamp": start,
                "message": {"role": "user", "content": "go"}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant", "timestamp": start,
                "message": {"content": [
                    {"type": "tool_use", "name": "Read", "id": "t1",
                     "input": {}}]}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant", "timestamp": start,
                "message": {"content": [
                    {"type": "text", "text": body}]}}) + "\n")
        payload = {"transcript_path": path, "cwd": self.repo,
                   "stop_hook_active": False}
        env = dict(os.environ,
                   STOP_STATE=os.path.join(self.room, "state.json"),
                   STOP_LOG=os.path.join(self.room, "state.log"),
                   STOP_HOLDOUT="0")
        settle.once(payload, env)
        self.assertIn('"cheap": "busy"', self.logged())

    def test_four_hour_announce_still_blocks(self):
        from datetime import datetime, timedelta, timezone
        start = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        path = os.path.join(self.room, "four-ann.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "type": "user", "timestamp": start,
                "message": {"role": "user", "content": "go"}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant", "timestamp": start,
                "message": {"content": [
                    {"type": "tool_use", "name": "Read", "id": "t1",
                     "input": {}}]}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant", "timestamp": start,
                "message": {"content": [
                    {"type": "text",
                     "text": "Next steps: wire the HTTP client."}]}}) + "\n")
        payload = {"transcript_path": path, "cwd": self.repo,
                   "stop_hook_active": False}
        env = dict(os.environ,
                   STOP_STATE=os.path.join(self.room, "state.json"),
                   STOP_LOG=os.path.join(self.room, "state.log"),
                   STOP_HOLDOUT="0")
        _, out = settle.once(payload, env)
        self.assertIn("YOU ALREADY HAVE PERMISSION", out)

    def test_grok_events_clock_four_hours(self):
        from datetime import datetime, timedelta, timezone
        start = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        path = os.path.join(self.room, "chat_history.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "type": "user",
                "content": [{"type": "text", "text": "go"}]}) + "\n")
        events = os.path.join(self.room, "events.jsonl")
        with open(events, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "type": "turn_started", "ts": start,
                "turn_number": 1}) + "\n")
        self.assertTrue(gate.busy(path))

    def test_failed_path_with_high_sibling_blocks(self):
        store = os.path.join(self.room, "decisions.json")
        with open(store, "w", encoding="utf-8") as handle:
            json.dump({"last": "regex", "nodes": [
                {"id": "regex", "label": "add a leftover pattern",
                 "score": 0.8, "status": "failed", "next": ["payload"]},
                {"id": "payload", "label": "read the closing from the payload",
                 "score": 0.7, "status": "open", "next": []},
            ]}, handle)
        _, out = self.fire([
            ("user", "go"),
            ("t1", "Read"),
            ("say", "Regex missed it. Stopping."),
        ])
        self.assertIn("THE TREE STILL HAS A PATH", out)

    def test_leftover_next_pass_blocks(self):
        body = (
            "I read the five TeX files. The verdict is revise communication. "
            "Ten notes follow, none of them structure. "
        ) * 6 + "Next pass is those ten captions and openers."
        _, out = self.fire([
            ("user", "go"),
            ("t1", "Read"),
            ("t2", "Read"),
            ("t3", "Read"),
            ("say", body),
        ])
        self.assertIn("YOU ALREADY HAVE PERMISSION", out)


if __name__ == "__main__":
    unittest.main()
