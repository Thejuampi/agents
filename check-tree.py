#!/usr/bin/env python3
"""Stop hook. The tree still has a path.

Work forks. The agent scores options and takes one. When that path
fails, the next highest remaining option is still work. A stop that
leaves it on the table is leftover.

The tree lives next to the session transcript as decisions.json,
or at <cwd>/.grok/decisions.json. Score is judgment. A low-score
node waits while a higher one is still open, unless it sits next
to the node just processed.

A closing that names leftover options without a tree file still fires.
"""
import importlib.util
import json
import os
import re
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

perm = mod.load("check-permission.py")

FAILED = {"failed", "fail", "miss", "dead"}
TAKEN = {"taken", "done", "ok", "passed", "success"}
SKIPPED = {"skipped", "skip", "low"}
BAND = 0.7

LEFT = re.compile(
    r"("
    r"left unexplored|"
    r"unexplored (path|option|approach)|"
    r"did not (try|explore|attempt) the other|"
    r"other (paths?|options?|approaches?) remains?|"
    r"remaining (paths?|options?|approaches?)|"
    r"could also try|"
    r"left on the table|"
    r"will not explore|"
    r"skipped the other|"
    r"sin (probar|explorar) la otra|"
    r"quedan? (opciones?|caminos?|enfoques?)|"
    r"no (prob[eé]|explor[eé]) (la otra|el otro)|"
    r"el (otro|siguiente) (camino|enfoque) sigue"
    r")",
    re.IGNORECASE,
)

REMINDER = """KEEP GOING - THE TREE STILL HAS A PATH

Next: {label} (score {score}).
The last path is done or failed. Take this node now. Update the tree file when you finish it."""

NAMED = """KEEP GOING - YOU NAMED A PATH YOU DID NOT TAKE

{hits}

Go back to the options you listed. Score them. Take the next one."""


def _as_status(node):
    raw = str((node or {}).get("status") or "open").strip().lower()
    if raw in FAILED:
        return "failed"
    if raw in TAKEN:
        return "taken"
    if raw in SKIPPED:
        return "skipped"
    return "open"


def score_of(node):
    raw = (node or {}).get("score", 0)
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if n > 1.0:
        return min(1.0, n / 10.0) if n <= 10 else 1.0
    return max(0.0, min(1.0, n))


def _neighbours(nodes, last_id):
    ids = set()
    if not last_id:
        return ids
    for node in nodes:
        nid = str(node.get("id") or "")
        nxt = node.get("next") or []
        if not isinstance(nxt, list):
            nxt = []
        links = [str(x) for x in nxt]
        if nid == last_id:
            ids.update(links)
        if last_id in links:
            ids.add(nid)
    return ids


def _high_band(open_nodes):
    if not open_nodes:
        return []
    best = max(score_of(n) for n in open_nodes)
    return [n for n in open_nodes if score_of(n) >= best * BAND]


def _pick_from(candidates, adjacent_ids):
    if not candidates:
        return None
    adj = [n for n in candidates if str(n.get("id") or "") in adjacent_ids]
    pool = adj or candidates
    return max(pool, key=score_of)


def next_path(tree):
    nodes = list((tree or {}).get("nodes") or [])
    open_nodes = [n for n in nodes if _as_status(n) == "open"]
    if not open_nodes:
        return None
    last_id = str((tree or {}).get("last") or "")
    last = next((n for n in nodes if str(n.get("id") or "") == last_id), None)
    adj = _neighbours(nodes, last_id)
    last_status = _as_status(last) if last else "failed"
    high = _high_band(open_nodes)
    if last_status == "taken":
        cont = [n for n in high if str(n.get("id") or "") in adj]
        return _pick_from(cont, adj)
    chosen = _pick_from(high, adj)
    if chosen:
        return chosen
    return _pick_from(open_nodes, adj)


def tree_path(payload):
    env = os.environ.get("STOP_TREE")
    if env:
        return env
    found = []
    transcript = payload.get("transcript_path") or ""
    if transcript:
        found.append(os.path.join(os.path.dirname(
            os.path.abspath(transcript)), "decisions.json"))
    cwd = payload.get("cwd") or os.getcwd()
    found.append(os.path.join(cwd, ".grok", "decisions.json"))
    for path in found:
        if os.path.exists(path):
            return path
    return found[0]


def load_tree(payload):
    path = tree_path(payload)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _leftover(message):
    hits = []
    for found in LEFT.finditer(message):
        text = found.group(0).strip()
        if text.lower() not in [h.lower() for h in hits]:
            hits.append(text)
    return hits


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("stop_hook_active"):
        return 0

    raw = perm.closing_of(payload)
    if not raw:
        return 0
    message = perm.unquoted(raw)

    loaded = load_tree(payload)
    node = next_path(loaded) if loaded else None
    if node:
        label = str(node.get("label") or node.get("id") or "open node")
        sys.stderr.write(REMINDER.format(
            label=label, score=round(score_of(node), 2)) + "\n")
        return 2

    hits = _leftover(message)
    if not hits:
        return 0
    sys.stderr.write(NAMED.format(
        hits="\n".join("  - " + h for h in hits[:4])) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
