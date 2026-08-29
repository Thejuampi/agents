#!/usr/bin/env bash
# Every suite, one command. A pattern or a checker that breaks another one
# shows up here before it reaches a live session.
cd "$(dirname "$0")" || exit 1
fail=0
for suite in test_*.py; do
  printf '%-28s ' "$suite"
  if ! python "$suite" 2>/dev/null | tail -1; then fail=1; fi
done
rm -f .stop-state.json
exit $fail
