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
if python3 scripts/loop_control.py status; then
    exit 1
else
    rc=$?
    [ "$rc" -eq 1 ] || exit "$rc"
fi
nohup uv run python -u run_autoresearch_loop.py >> autoresearch.out 2>&1 &
echo "Autoresearch launcher started (PID $!). See $REPO/autoresearch.out."
