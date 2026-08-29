#!/usr/bin/env bash
# PAPER.md is the source. This turns it into paper.pdf.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd "$here"
export PATH="$HOME/AppData/Local/Programs/MiKTeX/miktex/bin/x64:$PATH"
python md2tex.py
pdflatex -interaction=nonstopmode -halt-on-error paper.tex >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error paper.tex >/dev/null
echo "paper.pdf: $(pdfinfo paper.pdf 2>/dev/null | grep Pages || echo built)"
