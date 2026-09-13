#!/usr/bin/env bash
# Hand off from the standalone arm-2 fit to the full study chain.
#
# arm 2 was launched directly (fit_anchor10cov_s2.sh) before the gate had passed.
# run_arm_sequence.sh skips arms whose MESHES exist, but it cannot see a fit that
# is still running -- it would start a second concurrent fit of the same arm and
# both would lose. So wait for arm 2 to land, then start the chain, which then
# has nothing left to fit for arms 1 and 2 and proceeds to renders.
#
# Waits on the MESHES, not on satisfaction_metrics_fitted.json: fit_spiral.py
# writes that json about a minute BEFORE the meshes, and a driver keyed to it
# wakes early and silently drops the arm. That race cost an arm once already.
set -uo pipefail
S=/home/jon/openclaw-workspace/Neo-VM/spiral_out
TAG=anchor10cov_s2
DEADLINE=$(( $(date +%s) + 5*3600 ))   # generous; a fit here takes ~2h

while :; do
  d=$(ls -d "$S"/*patch_"$TAG"/meshes/fitted_"$TAG" 2>/dev/null | head -1 || true)
  if [ -n "$d" ]; then
    n=$(ls -d "$d"/w*_"$TAG" 2>/dev/null | grep -v spliced | wc -l)
    if [ "$n" -ge 120 ] && ! pgrep -f "[f]it_spiral.py" >/dev/null 2>&1; then
      echo "$(date -Is) arm 2 meshes complete ($n windings) and no fit running; starting chain"
      exec "$S/run_anchor_ablation.sh"
    fi
    echo "$(date -Is) meshes present but n=$n or fit still running; waiting"
  fi
  if [ "$(date +%s)" -gt "$DEADLINE" ]; then
    echo "$(date -Is) DEADLINE passed without arm 2 completing; NOT starting the chain" >&2
    exit 1
  fi
  sleep 120
done
