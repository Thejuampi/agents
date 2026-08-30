#!/usr/bin/env python3
"""Re-runs the judge prompt ablation on the clean corpus.

Three closing instructions over the same rows, changing nothing else. The
first ablation ran on the contaminated corpus and on a prompt that has since
changed; these are the numbers the paper reports."""
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def load(alias, filename):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


judge = load("judge", "llm_judge.py")

CRITERION = "The test is whether there is a concrete action"
FINAL = "When unsure, answer"


def variant(kind):
    lines = judge.STOP_SYSTEM.split(chr(10))
    if kind != "strict":
        lines = [l for l in lines if not l.startswith(CRITERION)]
    out = []
    for line in lines:
        if line.startswith(FINAL):
            line = "When unsure, answer STOP." if kind == "base" \
                else "When unsure, answer OK."
        out.append(line)
    return chr(10).join(out)


def framed(row):
    message = row["closing"]
    asked = row.get("asked") or ""
    if asked:
        return f"[the user asked: {asked.strip()[:400]}]{chr(10)}{message}"
    return message


def run(kind, rows, step=50):
    system = variant(kind)
    start = time.time()
    fires = caught = 0
    hits = sum(1 for r in rows if r.get("push"))
    for i, row in enumerate(rows):
        if i % step == 0:
            print(kind, i, int(time.time() - start), "s", flush=True)
        text, _ = judge._chat(system, judge.STOP_SHOTS, framed(row), 45)
        if judge._pick(text, "OK", "STOP") != "STOP":
            continue
        fires += 1
        caught += 1 if row.get("push") else 0
    prec = caught / max(fires, 1)
    rec = caught / max(hits, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return kind, fires, prec, rec, f1


def corpus_path():
    """The corpus a table was computed on, not whichever one is newest."""
    for arg in sys.argv[1:]:
        if arg.endswith(".json"):
            return arg if os.path.isabs(arg) else os.path.join(HERE, arg)
    return os.path.join(HERE, "corpus.json")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = json.load(open(corpus_path(), encoding="utf-8"))
    rows = [r for r in data if not r.get("noise")]
    limit = [a for a in sys.argv[1:] if not a.endswith(".json")]
    if limit:
        rows = rows[:int(limit[0])]
    print(len(rows), "rows", sum(1 for r in rows if r.get("push")), "pushes")
    got = [run(kind, rows) for kind in ("base", "loose", "strict")]
    print()
    for kind, fires, prec, rec, f1 in got:
        print(f"{kind:8} {fires:4}  {prec:.3f}  {rec:.3f}  {f1:.3f}")


if __name__ == "__main__":
    main()
