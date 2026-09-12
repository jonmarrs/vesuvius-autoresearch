#!/usr/bin/env bash
# Score both outer-winding arms sequentially with the serial-fold path.
# Three concurrent folds OOM a 32GB box on a 352M-px strip (fold rc=-9, SIGKILL),
# so INK_METRIC_SERIAL_FOLDS=1 runs one fold at a time and accumulates the
# ensemble in place. Verified against a previously scored arm: the gate changes
# the answer by less than the scorer's own run-to-run nondeterminism.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
VENV=/home/jon/openclaw-workspace/Neo-VM/data/ink_scorer_venv/bin/python
export INK_METRIC_SERIAL_FOLDS=1

for ARM in outer_baseline01 outer_gap133; do
  echo "=================== SCORE $ARM $(date -Is) ==================="
  ls "$SO/$ARM/meshes/ink"/*.jpg >/dev/null 2>&1 || { echo "[fail] no ink strips for $ARM"; continue; }
  rm -rf "$SO/$ARM/ink_metric" "$SO/$ARM/meshes/ink_metric"
  ( while true; do
      free -m | awk '/^Mem:/{printf "[mem] used=%dMB avail=%dMB\n",$3,$7}'
      sleep 30
    done ) & MEMPID=$!
  ( cd "$SO/$ARM/spiral-fitting" && \
    "$VENV" -u get_ink_metrics.py "$SO/$ARM/meshes/ink" --output "$SO/$ARM/ink_metric" )
  echo "[exit] $ARM scoring rc=$?"
  kill $MEMPID 2>/dev/null
done
echo "=================== ALL DONE $(date -Is) ==================="
