#!/usr/bin/env bash
# Run the registered n=4 vs n=3 analysis when the last gap render is scored.
# File-based wait, never a process match.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
R=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch

echo "[wait] for outer_gap133s3 to be scored $(date -Is)"
DEADLINE=$(( $(date +%s) + 24*3600 ))
until [ -f "$SO/outer_gap133s3/ink_metric/metrics.json" ]; do
  [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] not scored within 9h"; exit 1; }
  sleep 60
done
echo "[wait] all seven arms present $(date -Is)"

declare -A FIT=(
  [baseline01]=2026-08-28_s1_slice-13056-18432_38442-patch_baseline01
  [seed02]=2026-08-29_s1_slice-13056-18432_38442-patch_seed02
  [seed03]=2026-08-31_s1_slice-13056-18432_38442-patch_seed03
  [seed04]=2026-08-31_s1_slice-13056-18432_38442-patch_seed04
  [gap133]=2026-09-01_s1_slice-13056-18432_38442-patch_gap133
  [gap133s2]=2026-09-01_s1_slice-13056-18432_38442-patch_gap133s2
  [gap133s3]=2026-09-02_s1_slice-13056-18432_38442-patch_gap133s3
)
ARGS=()
for S in baseline01 seed02 seed03 seed04 gap133 gap133s2 gap133s3; do
  d=$(ls -d "$SO"/*patch_"$S" 2>/dev/null | head -1)
  [ -n "$d" ] || { echo "[fail] no fit dir for $S"; exit 1; }
  ARGS+=("$S=$SO/outer_$S/ink_metric/metrics.json,$d/satisfaction_metrics_fitted.json")
done
echo "=========== PRIMARY (registered) ==========="
python3 "$R/scripts/analyse_gap_ink_arm.py" "${ARGS[@]}" --out "$SO/gap_ink_arm_n7.json"
primary_rc=$?

# The registered SECONDARY (addendum A). Wired in so a registered analysis cannot
# be quietly forgotten -- that is the failure a registration is supposed to stop.
# Metrics-only args: this one reads strips[0], not the satisfaction json.
echo
echo "=========== SECONDARY (registered, exploratory) ==========="
SARGS=()
for S in baseline01 seed02 seed03 seed04 gap133 gap133s2 gap133s3; do
  SARGS+=("$S=$SO/outer_$S/ink_metric/metrics.json")
done
python3 "$R/scripts/analyse_gap_contrast_exploratory.py" "${SARGS[@]}" \
  --out "$SO/gap_contrast_exploratory_n7.json"
echo "[analysis] primary rc=$primary_rc secondary rc=$?"
