#!/usr/bin/env bash
# Verify the 9daa477e0 bump once the second look stops using 26GB of RAM.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
R=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
echo "[wait] for the second-look sequence to finish $(date -Is)"
DEADLINE=$(( $(date +%s) + 48*3600 ))
until grep -q "SECOND LOOK ARMS DONE" "$SO/second_look.log" 2>/dev/null; do
  [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] sequence unfinished after 48h"; exit 1; }
  sleep 300
done
sleep 60
echo "[run] full suite after the 9daa477e0 bump $(date -Is)"
cd "$R" && .venv/bin/python -m pytest -q 2>&1 | tail -12
