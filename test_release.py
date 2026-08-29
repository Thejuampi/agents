#!/usr/bin/env python3
"""The release phrase is the lock on the only door that is not work. These are
the ways an agent would try the handle."""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("release", os.path.join(HERE, "release.py"))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class Phrase(unittest.TestCase):
    def setUp(self):
        self.parts = release.mint()
        self.phrase = release.render(self.parts)

    def test_a_fresh_phrase_is_never_the_last_one(self):
        self.assertNotEqual(self.parts, release.mint())

    def test_the_whole_phrase_after_the_claim_opens_it(self):
        self.assertTrue(release.presented(
            f"BLOCKED: no credential on this host.\n\n    {self.phrase}", self.parts))

    def test_the_bare_word_opens_nothing(self):
        self.assertFalse(release.presented("BLOCKED: I need your input.", self.parts))

    def test_out_of_order_is_a_miss(self):
        shuffled = release.render(self.parts[::-1])
        self.assertFalse(release.presented(f"BLOCKED: x\n{shuffled}", self.parts))

    def test_a_partial_phrase_is_a_miss(self):
        half = release.render(self.parts[:2])
        self.assertFalse(release.presented(f"BLOCKED: x\n{half}", self.parts))

    def test_a_phrase_from_an_earlier_block_is_a_miss(self):
        self.assertFalse(release.presented(
            f"BLOCKED: x\n{release.render(release.mint())}", self.parts))

    def test_the_phrase_without_a_claim_is_a_miss(self):
        self.assertFalse(release.presented(f"All done.\n{self.phrase}", self.parts))

    def test_the_phrase_before_the_claim_is_a_miss(self):
        self.assertFalse(release.presented(f"{self.phrase}\nBLOCKED: x", self.parts))

    def test_no_phrase_issued_means_nothing_opens_it(self):
        self.assertFalse(release.presented(f"BLOCKED: x\n{self.phrase}", []))

    def test_line_wrapping_does_not_break_it(self):
        wrapped = "\n   ".join(self.parts)
        self.assertTrue(release.presented(f"BLOCKED: x\n   {wrapped}", self.parts))

    def test_case_does_not_matter(self):
        self.assertTrue(release.presented(
            f"blocked: x\n{self.phrase.upper()}", self.parts))

    def test_a_plain_claim_is_a_claim(self):
        self.assertTrue(release.claims_block("BLOCKED: no keystore on this host."))

    def test_naming_the_marker_in_code_is_not_claiming_one(self):
        self.assertFalse(release.claims_block(
            "The old escape was the literal string `BLOCKED:`, sitting in six "
            "files: read one, type it, walk. All six are closed."))

    def test_quoting_the_marker_is_not_claiming_one(self):
        self.assertFalse(release.claims_block(
            'The checker used to let a message through the moment it said '
            '"BLOCKED:" and that was the whole hole.'))

    def test_a_fenced_example_is_not_claiming_one(self):
        self.assertFalse(release.claims_block(
            "Here is what it used to match:\n```\nBLOCKED: anything\n```\nFixed."))


if __name__ == "__main__":
    unittest.main(verbosity=2)
