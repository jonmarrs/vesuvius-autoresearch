#!/usr/bin/env bash
# Full test suite after the villa bump, deferred until the gap arm stops using
# 26GB of RAM. Waits on the analysis output file, never on a process name.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
R=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
echo "[wait] for the gap arm to finish $(date -Is)"
DEADLINE=$(( $(date +%s) + 24*3600 ))
until [ -f "$SO/gap_ink_arm_n7.json" ]; do
  [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] arm unfinished after 10h"; exit 1; }
  sleep 120
done
sleep 60   # let the scorer's memory actually be released
echo "[run] full suite after villa bump $(date -Is)"
cd "$R" && .venv/bin/python -m pytest -q 2>&1 | tail -25
