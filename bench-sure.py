#!/usr/bin/env python3
"""Does the judge's confidence tell right verdicts from wrong ones?

The number is read from the logprobs on every verdict and written to the log,
and it has never decided anything. A floor is only worth having if the wrong
verdicts sit below the right ones. This asks the gold sets that question."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(HERE, "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

judge = mod.load("llm_judge.py")
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0]]
gold = mod.load("test_stop_judge.py", "gold")


def rows():
    for want, text in gold.CASES:
        got, _ = judge.stop_verdict(text)
        yield want, got, judge.sureness(), text
    for want, asked, text in gold.ASKED:
        got, _ = judge.stop_verdict(text, asked=asked)
        yield want, got, judge.sureness(), text


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    right, wrong = [], []
    for want, got, sure, text in rows():
        (right if want == got else wrong).append((sure, want, got, text))
    for label, group in (("right", right), ("wrong", wrong)):
        if not group:
            continue
        scores = sorted(s for s, _, _, _ in group)
        print(f"{label}: {len(group)} cases, "
              f"lowest {scores[0]:.3f}, median {scores[len(scores) // 2]:.3f}, "
              f"highest {scores[-1]:.3f}")
    for sure, want, got, text in sorted(right + wrong)[:8]:
        mark = "ok " if want == got else "BAD"
        print(f"  {sure:.3f} {mark} want {want:4} got {got:4} {text[:56]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
