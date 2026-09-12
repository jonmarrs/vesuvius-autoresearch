#!/usr/bin/env bash
# Run the registered n=4 analysis the moment seed03's metrics land. Not before:
# the pre-registration fixes n=4, and a peek at n=3 is a peek.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
R=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
until [ -f "$SO/outer_seed03/ink_metric/metrics.json" ]; do sleep 20; done
sleep 5
declare -A FIT=(
  [baseline01]=2026-08-28_s1_slice-13056-18432_38442-patch_baseline01
  [seed02]=2026-08-29_s1_slice-13056-18432_38442-patch_seed02
  [seed03]=2026-08-31_s1_slice-13056-18432_38442-patch_seed03
  [seed04]=2026-08-31_s1_slice-13056-18432_38442-patch_seed04
)
ARGS=()
for S in baseline01 seed02 seed03 seed04; do
  ARGS+=("$S=$SO/outer_$S/ink_metric/metrics.json,$SO/${FIT[$S]}/satisfaction_metrics_fitted.json")
done
python3 "$R/scripts/analyse_outer_floor.py" "${ARGS[@]}" --out "$SO/outer_floor_n4.json"
