#!/usr/bin/env python3
"""The Stop hook end to end, as the harness runs it: a transcript on disk, a
JSON payload on stdin, an exit code and a message out.

The local model is real here. These assert the gate, not the model's taste, so
they use messages a 9B has no trouble with.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "check-stop.py")


def transcript(path, turns):
    with open(path, "w", encoding="utf-8") as handle:
        for kind, payload in turns:
            if kind == "user":
                entry = {"type": "user", "message": {"role": "user", "content": payload}}
            elif kind == "say":
                entry = {"type": "assistant",
                         "message": {"content": [{"type": "text", "text": payload}]}}
            else:
                entry = {"type": "assistant",
                         "message": {"content": [{"type": "tool_use", "name": payload,
                                                  "id": "t", "input": {}}]}}
            handle.write(json.dumps(entry) + "\n")


class Gate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.room = tempfile.mkdtemp(prefix="stopgate-")
        cls.state = os.path.join(cls.room, "state.json")
        cls.repo = os.path.join(cls.room, "repo")
        os.makedirs(cls.repo)
        with open(os.path.join(cls.repo, "README.md"), "w") as handle:
            handle.write("# repo\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.room, ignore_errors=True)

    def run_hook(self, turns, chained=False, name="t.jsonl"):
        path = os.path.join(self.room, name)
        transcript(path, turns)
        payload = json.dumps({"transcript_path": path, "cwd": self.repo,
                              "stop_hook_active": chained})
        env = dict(os.environ, STOP_STATE=self.state)
        done = subprocess.run([sys.executable, HOOK], input=payload,
                              capture_output=True, text=True, timeout=180, env=env)
        return done.returncode, done.stderr

    def test_a_question_is_blocked_before_the_model_is_asked(self):
        code, out = self.run_hook([("user", "go"), ("tool", "Read"),
                                   ("say", "Should I wire it up now?")])
        self.assertEqual(2, code, out)

    def test_finished_work_ends_the_turn(self):
        code, out = self.run_hook([("user", "go"), ("tool", "Edit"), ("tool", "Bash"),
                                   ("say", "Done. The suite is green and the "
                                           "change is committed.")])
        self.assertEqual(0, code, out)

    def test_the_bare_word_blocked_is_not_an_exit(self):
        code, out = self.run_hook([("user", "go"), ("tool", "Read"),
                                   ("say", "BLOCKED: I need you to tell me which "
                                           "approach you prefer.")])
        self.assertEqual(2, code)
        self.assertIn("NOT A PASSWORD", out)

    def test_the_first_block_hands_out_a_phrase(self):
        code, out = self.run_hook([("user", "go"), ("tool", "Read"),
                                   ("say", "Should I continue?")], name="p.jsonl")
        self.assertEqual(2, code)
        self.assertIn("this line exactly", out)

    def test_a_fake_blocker_does_not_survive_the_phrase(self):
        name = "fake.jsonl"
        _, first = self.run_hook([("user", "go"), ("tool", "Read"),
                                  ("say", "Shall I proceed?")], name=name)
        phrase = self.phrase_from(first)
        code, out = self.run_hook(
            [("user", "go"), ("tool", "Read"),
             ("say", "BLOCKED: I cannot responsibly choose between these two "
                     "designs without your product judgement, and guessing "
                     "would risk substantial rework.\n\n" + phrase)],
            chained=True, name=name)
        self.assertIn("DID NOT SURVIVE THE AUDIT", out)

    def test_a_real_blocker_with_the_phrase_ends_the_turn(self):
        name = "real.jsonl"
        _, first = self.run_hook([("user", "go"), ("tool", "Read"),
                                  ("say", "Shall I proceed?")], name=name)
        phrase = self.phrase_from(first)
        code, out = self.run_hook(
            [("user", "go"), ("tool", "Bash"), ("tool", "Bash"), ("tool", "Bash"),
             ("say", "BLOCKED: the upload needs the production API token. "
                     "curl returns 401 and no credential is set in the "
                     "environment.\n\n" + phrase)],
            chained=True, name=name)
        self.assertEqual(0, code, out)

    def phrase_from(self, text):
        for line in text.splitlines():
            if line.strip().count("-") >= 4 and len(line.split()) == 4:
                return line.strip()
        self.fail("no phrase issued:\n" + text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
