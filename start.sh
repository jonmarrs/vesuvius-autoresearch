#!/bin/bash
# Start from this checkout regardless of the caller's current directory.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
if [ "${1:-}" = "--watchdog" ]; then
    [ ! -f .loop_paused ] || exit 0
else
    rm -f .loop_paused
fi
status=$(python3 scripts/loop_control.py status) && rc=0 || rc=$?
[ -z "$status" ] || echo "$status"
if [ "$rc" -eq 0 ]; then
    exit 1
fi
[ "$rc" -eq 1 ] || exit "$rc"
nohup uv run python -u run_autoresearch_loop.py >> autoresearch.out 2>&1 &
echo "Autoresearch launcher started (PID $!). See $REPO/autoresearch.out."
case "$status" in
*"Unsupervised training run"*)
    # The loop's start refuses beside such a run (and stops a loop's run past
    # any cycle's timeout); said here, not only in autoresearch.out.
    echo "It will not start a cycle while the run above goes on. ./stop.sh stops a run" \
        "a loop or ablation started (and pauses the watchdog); a run started by hand" \
        "is yours to stop. The watchdog tries again on its next tick."
    ;;
esac
