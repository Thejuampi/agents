#!/usr/bin/env bash
# Every suite, one command. A pattern or a checker that breaks another one
# shows up here before it reaches a live session.
#
# The ledger runs with it: every child any suite starts is written down, and
# test_spawn.py reads the count last and fails when the budget is spent.
cd "$(dirname "$0")" || exit 1
fail=0
export STOP_SPAWN_LOG="$(mktemp)"
for suite in test_*.py; do
  if [ "$suite" = "test_spawn.py" ]; then continue; fi
  printf '%-28s ' "$suite"
  if ! python "$suite" 2>/dev/null | tail -1; then fail=1; fi
done
printf '%-28s ' "test_spawn.py"
STOP_SPAWN_COUNT="$(wc -l < "$STOP_SPAWN_LOG")"
export STOP_SPAWN_COUNT
if ! python test_spawn.py 2>/dev/null | tail -1; then fail=1; fi
rm -f "$STOP_SPAWN_LOG" .stop-state.json
exit $fail
