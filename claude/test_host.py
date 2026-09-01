#!/usr/bin/env python3
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

host = mod.load("host.py")
reader = mod.load("transcript.py")
hints = mod.load("candidates.py")
settle = mod.load("settle.py")


def dump(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


GROK_USER = {"type": "user", "content": [
    {"type": "text", "text": "<user_query>\ngo\n</user_query>"}]}
GROK_WRITE = {
    "type": "assistant",
    "content": "Should I wire it up now?",
    "tool_calls": [{
        "id": "c1",
        "name": "write",
        "arguments": json.dumps({"file_path": "src/Foo.kt", "content": "x"}),
    }],
}
GROK_RESULT = {"type": "tool_result", "tool_call_id": "c1", "content": "ok"}
GROK_SYN = {"type": "user", "synthetic_reason": "system_reminder",
            "content": [{"type": "text", "text": "ignore me"}]}


class Detect(unittest.TestCase):
    def test_claude_payload_is_detected(self):
        self.assertEqual("claude", host.detect(
            {"transcript_path": "t.jsonl", "stop_hook_active": False, "cwd": "/x"},
            {}))

    def test_grok_env_is_detected(self):
        self.assertEqual("grok", host.detect({}, {"GROK_SESSION_ID": "abc"}))

    def test_grok_camel_payload_is_detected(self):
        self.assertEqual("grok", host.detect(
            {"stopHookActive": False, "sessionId": "abc"}, {}))

    def test_transcript_path_wins_over_grok_env(self):
        self.assertEqual("claude", host.detect(
            {"transcript_path": "t.jsonl", "stop_hook_active": False},
            {"GROK_SESSION_ID": "abc"}))


class Ignore(unittest.TestCase):
    def test_session_end_is_ignored(self):
        seen = host.view({"reason": "shutdown", "stopHookActive": False},
                         {"GROK_SESSION_ID": "abc"})
        self.assertTrue(seen.ignore)

    def test_end_turn_is_not_ignored(self):
        seen = host.view({"reason": "end_turn", "stopHookActive": False},
                         {"GROK_SESSION_ID": "abc"})
        self.assertFalse(seen.ignore)

    def test_missing_reason_is_not_ignored(self):
        seen = host.view({"stopHookActive": False}, {"GROK_SESSION_ID": "abc"})
        self.assertFalse(seen.ignore)


class Project(unittest.TestCase):
    def setUp(self):
        self.room = tempfile.mkdtemp(prefix="host-")
        self.path = os.path.join(self.room, "chat_history.jsonl")
        dump(self.path, [GROK_USER, GROK_WRITE, GROK_RESULT, GROK_SYN])

    def test_projected_user_spoke(self):
        rows = [r for r in host.entries(self.path) if reader.spoke(r)]
        self.assertEqual(1, len(rows))

    def test_projected_synthetic_is_silent(self):
        kinds = [r.get("type") for r in host.entries(self.path)]
        self.assertNotIn("system_reminder", json.dumps(kinds))

    def test_projected_user_keeps_a_timestamp(self):
        path = os.path.join(self.room, "stamped.jsonl")
        dump(path, [{"type": "user", "timestamp": "2026-08-30T12:00:00Z",
                     "content": [{"type": "text", "text": "go"}]}])
        rows = list(host.entries(path))
        self.assertEqual("2026-08-30T12:00:00Z", rows[0].get("timestamp"))

    def test_projected_write_is_a_candidate(self):
        written = []
        for row in host.entries(self.path):
            written += hints.written(row)
        self.assertEqual(["src/Foo.kt"], written)

    def test_claude_entries_passthrough(self):
        path = os.path.join(self.room, "claude.jsonl")
        dump(path, [{"type": "assistant", "message": {"content": [
            {"type": "text", "text": "done"}]}}])
        rows = list(host.entries(path))
        self.assertEqual("done", rows[0]["message"]["content"][0]["text"])


class Locate(unittest.TestCase):
    def setUp(self):
        self.room = tempfile.mkdtemp(prefix="grokhome-")
        self.cwd = r"C:\work\app"
        self.sid = "sess-1"
        self.env = {"GROK_HOME": self.room, "GROK_SESSION_ID": self.sid}

    def test_locator_finds_encoded_cwd(self):
        target = (Path(self.room) / "sessions" / quote(self.cwd, safe="")
                  / self.sid / "chat_history.jsonl")
        target.parent.mkdir(parents=True)
        target.write_text("{}\n", encoding="utf-8")
        seen = host.view(
            {"stopHookActive": False, "sessionId": self.sid, "cwd": self.cwd,
             "reason": "end_turn"}, self.env)
        self.assertEqual(str(target), seen.path)

    def test_locator_globs_session_id(self):
        target = (Path(self.room) / "sessions" / "other-dir"
                  / self.sid / "chat_history.jsonl")
        target.parent.mkdir(parents=True)
        target.write_text("{}\n", encoding="utf-8")
        seen = host.view(
            {"stopHookActive": False, "sessionId": self.sid,
             "cwd": r"C:\wrong", "reason": "end_turn"}, self.env)
        self.assertEqual(str(target), seen.path)

    def test_last_message_from_payload(self):
        seen = host.view(
            {"stopHookActive": False, "lastAssistantMessage": "keep going?",
             "reason": "end_turn"}, {"GROK_SESSION_ID": "missing"})
        self.assertEqual("keep going?", seen.last_message())

    def test_empty_history_fail_opens_path(self):
        seen = host.view(
            {"stopHookActive": False, "reason": "end_turn"},
            {"GROK_SESSION_ID": "missing", "GROK_HOME": self.room})
        self.assertEqual("", seen.path)

    def test_background_tasks_flag_waiting(self):
        seen = host.view(
            {"stopHookActive": False, "backgroundTasks": [{"id": "1"}],
             "reason": "end_turn"}, {"GROK_SESSION_ID": "x"})
        self.assertTrue(bool(seen.waiting))

    def test_claude_payload_closing_is_used(self):
        seen = host.view(
            {"transcript_path": "t.jsonl", "stop_hook_active": False,
             "last_assistant_message": "Should I wire it up now?"}, {})
        self.assertEqual("Should I wire it up now?", seen.last_message())

    def test_claude_background_tasks_flag_waiting(self):
        seen = host.view(
            {"transcript_path": "t.jsonl", "stop_hook_active": False,
             "background_tasks": [{"id": "1"}]}, {})
        self.assertTrue(bool(seen.waiting))


class Gate(unittest.TestCase):
    def fire(self):
        from urllib.parse import quote
        room = tempfile.mkdtemp(prefix="grokgate-")
        repo = os.path.join(room, "repo")
        os.makedirs(repo)
        Path(repo, "README.md").write_text("# r\n", encoding="utf-8")
        sid = "sess-g"
        home = os.path.join(room, "ghome")
        target = Path(home) / "sessions" / quote(repo, safe="") / sid / "chat_history.jsonl"
        target.parent.mkdir(parents=True)
        target.write_text(
            json.dumps({"type": "user", "content": [
                {"type": "text", "text": "<user_query>go</user_query>"}]}) + "\n"
            + json.dumps({
                "type": "assistant",
                "content": "Should I wire it up now?",
                "tool_calls": [{"id": "t", "name": "read_file",
                                "arguments": json.dumps({"target_file": "a.kt"})}],
            }) + "\n",
            encoding="utf-8")
        payload = {"stopHookActive": False, "sessionId": sid, "cwd": repo,
                   "reason": "end_turn",
                   "lastAssistantMessage": "Should I wire it up now?"}
        env = dict(os.environ, STOP_STATE=os.path.join(room, "state.json"),
                   STOP_LOG=os.path.join(room, "state.log"),
                   GROK_HOME=home, GROK_SESSION_ID=sid)
        return settle.script(settle.HOOK, json.dumps(payload), env)

    def test_grok_question_blocks_on_patterns(self):
        done = self.fire()
        self.assertEqual(2, done.returncode, done.stderr)

    def test_grok_block_writes_decision_json(self):
        done = self.fire()
        self.assertEqual("block", json.loads(done.stdout)["decision"])


class Product(unittest.TestCase):
    def spec(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data.get("hooks", {}).get("Stop")

    def test_one_stop_definition_on_both_harnesses(self):
        repo = self.spec(os.path.join(HERE, "stop.json"))
        grok = self.spec(r"G:\grok\hooks\stop.json")
        claude = self.spec(Path.home() / ".claude" / "settings.json")
        self.assertEqual([repo, grok, claude], [repo, repo, repo])

    def test_live_wire_is_main_stop_only(self):
        data = json.loads(Path(r"G:\grok\hooks\stop.json").read_text(encoding="utf-8"))
        self.assertEqual(["Stop"], list(data.get("hooks") or {}))


class ClaudeCompat(unittest.TestCase):
    def fire(self):
        room = tempfile.mkdtemp(prefix="claudegate-")
        repo = os.path.join(room, "repo")
        os.makedirs(repo)
        Path(repo, "README.md").write_text("# r\n", encoding="utf-8")
        path = os.path.join(room, "t.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "type": "user",
                "message": {"role": "user", "content": "go"}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "tool_use", "name": "Read", "id": "t",
                     "input": {}}]}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "text",
                     "text": "Should I wire it up now?"}]}}) + "\n")
        payload = {"transcript_path": path, "cwd": repo,
                   "stop_hook_active": False, "hook_event_name": "Stop"}
        env = dict(os.environ,
                   STOP_STATE=os.path.join(room, "state.json"),
                   STOP_LOG=os.path.join(room, "state.log"))
        return settle.script(settle.HOOK, json.dumps(payload), env)

    def test_claude_payload_blocks_on_exit_2(self):
        done = self.fire()
        self.assertEqual(2, done.returncode)

    def test_claude_block_writes_no_decision_json(self):
        done = self.fire()
        self.assertFalse((done.stdout or "").lstrip().startswith("{"))

    def test_claude_payload_beats_a_stale_transcript(self):
        room = tempfile.mkdtemp(prefix="stale-")
        repo = os.path.join(room, "repo")
        os.makedirs(repo)
        Path(repo, "README.md").write_text("# r\n", encoding="utf-8")
        path = os.path.join(room, "t.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "type": "user",
                "message": {"role": "user", "content": "go"}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "tool_use", "name": "Read", "id": "t",
                     "input": {}}]}}) + "\n")
            handle.write(json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "text",
                     "text": "Done. The suite is green."}]}}) + "\n")
        payload = {
            "transcript_path": path, "cwd": repo,
            "stop_hook_active": False, "hook_event_name": "Stop",
            "last_assistant_message": "Should I wire it up now?",
        }
        env = dict(os.environ,
                   STOP_STATE=os.path.join(room, "state.json"),
                   STOP_LOG=os.path.join(room, "state.log"))
        done = settle.script(settle.HOOK, json.dumps(payload), env)
        self.assertEqual(2, done.returncode)


if __name__ == "__main__":
    unittest.main()
