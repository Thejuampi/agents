#!/usr/bin/env bash
# Assembles and compiles the paper. Sources are the paper-*.tex parts.
set -e
cd "$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64:$PATH"
python - <<'PY'
head = open("paper-head.tex", encoding="utf-8").read()
body = open("paper-body.tex", encoding="utf-8").read()
results = open("paper-results.tex", encoding="utf-8").read()
refs = open("paper-refs.tex", encoding="utf-8").read()
app = open("paper-appendix.tex", encoding="utf-8").read()
mark = chr(92) + "section{The self-labeling loop}"
assert mark in body, "the loop section anchors where results go"
before, after = body.split(mark, 1)
whole = head + before + results + mark + after + app + refs + chr(10) + chr(92) + "end{document}" + chr(10)
open("paper.tex", "w", encoding="utf-8").write(whole)
print("assembled", len(whole), "chars")
PY
pdflatex -interaction=nonstopmode -halt-on-error --enable-installer paper.tex >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error --enable-installer paper.tex >/dev/null
grep -c "^!" paper.log || true
grep "Output written" paper.log
