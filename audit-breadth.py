#!/usr/bin/env python3
"""Every pattern added is a chance to fire on something innocent, and a hook
that cries wolf gets ignored. This measures how wide each one really is.

The corpus is ordinary technical prose that is not an agent closing a turn:
the repo's own docs, read one paragraph at a time. A pattern that matches
there matches language, not the act of stopping.

Usage: audit-breadth.py [repo] [--top N]
"""
import glob
import importlib.util
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("perm", os.path.join(HERE, "check-permission.py"))
perm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perm)


def paragraphs(repo, cap=4000):
    """Prose from the repo's markdown, minus code blocks and tables."""
    out = []
    for pattern in ("**/*.md", "*.md"):
        for path in glob.iglob(os.path.join(repo, pattern), recursive=True):
            if os.sep + ".git" + os.sep in path:
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as handle:
                    body = handle.read()
            except OSError:
                continue
            body = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
            for block in body.split("\n\n"):
                text = block.strip()
                if len(text) < 60 or text.startswith("|") or text.startswith("#"):
                    continue
                out.append(text)
                if len(out) >= cap:
                    return out
    return out


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") \
        else os.environ.get("BREADTH_REPO") or os.getcwd()
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 20

    corpus = paragraphs(repo)
    if not corpus:
        print(f"no prose found under {repo}")
        return 1

    counts = []
    for label, compiled in perm.patterns_for(repo):
        hits = sum(1 for text in corpus if compiled.search(perm.unquoted(text)))
        if hits:
            counts.append((hits, label, compiled.pattern))

    counts.sort(reverse=True)
    total = sum(h for h, _, _ in counts)
    print(f"{len(corpus)} paragraphs of repo prose, {len(counts)} patterns matched, "
          f"{total} matches\n")
    for hits, label, pattern in counts[:top]:
        share = 100.0 * hits / len(corpus)
        print(f"{hits:5}  {share:5.1f}%  {label}: {pattern}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
