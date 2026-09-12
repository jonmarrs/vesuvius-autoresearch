#!/usr/bin/env bash
# Run the registered second-look analysis when all twelve arms are scored.
# The script itself refuses a partial sample, so this only decides WHEN, never
# whether. Waits on the twelfth metrics.json, never on a process name.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
R=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
BASE=(baseline01 seed02 seed03 seed04 seed05 seed06)
GAP=(gap133 gap133s2 gap133s3 gap133s4 gap133s5 gap133s6)

all_scored() {
  for t in "${BASE[@]}" "${GAP[@]}"; do
    [ -f "$SO/outer_$t/ink_metric/metrics.json" ] || return 1
  done
  return 0
}

echo "[wait] for all twelve arms $(date -Is)"
DEADLINE=$(( $(date +%s) + 48*3600 ))
until all_scored; do
  [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] not all arms scored within 48h"; exit 1; }
  sleep 300
done
echo "[wait] all twelve scored $(date -Is)"

ARGS=()
for t in "${BASE[@]}" "${GAP[@]}"; do
  d=$(ls -d "$SO"/*patch_"$t" 2>/dev/null | head -1)
  [ -n "$d" ] || { echo "[fail] no fit dir for $t"; exit 1; }
  ARGS+=("$t=$SO/outer_$t/ink_metric/metrics.json,$d/satisfaction_metrics_fitted.json")
done
python3 "$R/scripts/analyse_gap_ink_second_look.py" "${ARGS[@]}" \
  --out "$SO/gap_ink_second_look_n12.json"
