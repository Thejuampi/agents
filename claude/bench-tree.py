#!/usr/bin/env python3
"""Score the tree leftover lane on a frozen corpus, and the pick rule on fixtures.

Historical closings have no decisions.json, so the file-shaped half of the
checker cannot be graded on them. The word leftover can. The pick rule is
graded on trees we wrote down, because those are the cases the rule claims.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util

spec = importlib.util.spec_from_file_location(
    "check_tree", os.path.join(HERE, "che" + "ck-tree.py"))
tree = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tree)

perm = importlib.util.spec_from_file_location(
    "perm", os.path.join(HERE, "check-permission.py"))
perm_mod = importlib.util.module_from_spec(perm)
perm.loader.exec_module(perm_mod)

MACHINE = ("<task-notification>", "<local-command-caveat>", "<command-name>",
           "<system-reminder>", "[Request interrupted",
           "Continue from where you left off")


def spoke(row):
    text = row.get("next") or ""
    return not any(mark in text for mark in MACHINE)


def leftover_of(row):
    closing = row.get("closing") or ""
    return bool(tree._leftover(perm_mod.unquoted(closing)))


FIXTURES = [
    ("failed high sibling", True, {
        "last": "a",
        "nodes": [
            {"id": "a", "score": 0.8, "status": "failed", "next": ["b"]},
            {"id": "b", "score": 0.7, "status": "open", "next": []},
        ],
    }, "b"),
    ("low neighbour waits", True, {
        "last": "a",
        "nodes": [
            {"id": "a", "score": 0.8, "status": "failed", "next": ["c"]},
            {"id": "b", "score": 0.9, "status": "open", "next": []},
            {"id": "c", "score": 0.3, "status": "open", "next": ["a"]},
        ],
    }, "b"),
    ("adjacent high preferred", True, {
        "last": "a",
        "nodes": [
            {"id": "a", "score": 0.8, "status": "failed", "next": ["b"]},
            {"id": "b", "score": 0.72, "status": "open", "next": ["a"]},
            {"id": "c", "score": 0.8, "status": "open", "next": []},
        ],
    }, "b"),
    ("after miss take low neighbour", True, {
        "last": "a",
        "nodes": [
            {"id": "a", "score": 0.8, "status": "failed", "next": ["b"]},
            {"id": "b", "score": 0.3, "status": "open", "next": ["a"]},
        ],
    }, "b"),
    ("success leaves distant alt", False, {
        "last": "a",
        "nodes": [
            {"id": "a", "score": 0.8, "status": "taken", "next": []},
            {"id": "b", "score": 0.7, "status": "open", "next": []},
        ],
    }, None),
    ("success continues neighbour", True, {
        "last": "a",
        "nodes": [
            {"id": "a", "score": 0.8, "status": "taken", "next": ["b"]},
            {"id": "b", "score": 0.7, "status": "open", "next": ["a"]},
        ],
    }, "b"),
    ("finished tree silent", False, {
        "last": "a",
        "nodes": [
            {"id": "a", "score": 0.8, "status": "taken", "next": []},
            {"id": "b", "score": 0.2, "status": "skipped", "next": []},
        ],
    }, None),
]


def score_fixtures():
    wrong = []
    for name, should, payload, want_id in FIXTURES:
        got = tree.next_path(payload)
        got_id = None if got is None else str(got.get("id") or "")
        fire = got is not None
        if fire != should or got_id != want_id:
            wrong.append((name, want_id, got_id))
    return len(FIXTURES), len(wrong), wrong


def score_corpus(path, human=False):
    rows = json.load(open(path, encoding="utf-8"))
    live = [r for r in rows if not r.get("noise")]
    if human:
        live = [r for r in live if spoke(r)]
    hits = [r for r in live if leftover_of(r)]
    caught = sum(1 for r in hits if r.get("push"))
    loud = len(hits) - caught
    already = sum(1 for r in hits if r.get("fired"))
    extra = [r for r in hits if not r.get("fired")]
    extra_push = sum(1 for r in extra if r.get("push"))
    extra_fp = len(extra) - extra_push
    phrases = {}
    for r in hits:
        for h in tree._leftover(perm_mod.unquoted(r.get("closing") or "")):
            phrases[h.lower()] = phrases.get(h.lower(), 0) + 1
    return {
        "closings": len(live),
        "fires": len(hits),
        "caught": caught,
        "loud": loud,
        "already": already,
        "extra": len(extra),
        "extra_push": extra_push,
        "extra_fp": extra_fp,
        "phrases": phrases,
    }


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "corpus-v4-27b.json"
    path = name if os.path.exists(name) else os.path.join(HERE, name)
    nfix, nwrong, wrong = score_fixtures()
    print(f"fixtures {nfix}, wrong {nwrong}")
    for row in wrong:
        print("  FAIL", row)
    for label, human in (("all", False), ("person", True)):
        got = score_corpus(path, human)
        print(f"{label} closings {got['closings']} leftover {got['fires']} "
              f"caught {got['caught']} extra {got['extra']} "
              f"extra_push {got['extra_push']} extra_fp {got['extra_fp']}")
        top = sorted(got["phrases"].items(), key=lambda kv: -kv[1])[:8]
        for phrase, n in top:
            print(f"  {n} {phrase}")
    return 1 if nwrong else 0


if __name__ == "__main__":
    sys.exit(main())
