#!/usr/bin/env bash
# Re-score seed02 and seed03 once seed04's render is done. Both failed the first
# time because their work dirs were stock villa and the serial-fold gate was not
# in them; both are patched now. Waits so nothing competes for RAM.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
echo "[wait] for the seed04 driver to finish $(date -Is)"
while pgrep -f "run_outer_seeds.sh" >/dev/null 2>&1; do sleep 60; done
echo "[wait] driver gone $(date -Is)"
for S in seed02 seed03; do
  W="$SO/outer_$S"
  grep -q SERIAL_FOLDS "$W/spiral-fitting/get_ink_metrics.py" \
    || { echo "[fail] $S still unpatched, refusing"; continue; }
  echo "=================== RESCORE $S $(date -Is) ==================="
  "$REPO/repro/spiral_render/score_arms.sh" "$W" >> "$SO/outer_${S}_render.log" 2>&1
  echo "[rescore] $S rc=$? $(date -Is)"
  [ -f "$W/ink_metric/metrics.json" ] && echo "[ok] $S metrics.json written" \
    || echo "[fail] $S STILL no metrics.json"
done
echo "=================== RESCORE DONE $(date -Is) ==================="
