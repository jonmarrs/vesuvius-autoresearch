#!/usr/bin/env bash
# Step 2 of the recipe's mesh step: villa fit_spiral on the band z 9500-11000 with the recipe's overrides.
#
# usage: run_fit.sh ARM [STEPS]
#   ARM    recipe   the registered fit: 30,000 steps, the recipe's overrides, seed 1 (villa's default)
#          reduced  the same with fewer steps, only under the registration's reduced-fit rule
#          smoke    a few hundred steps to learn memory, time and the output layout; its windings are
#                   never compared with the published ones
#   STEPS  required for reduced and smoke; refused for recipe
#
# Writes R/work/fit_ARM/ (villa's own layout below it), R/logs/fit_ARM.log and a GPU-memory trace.
# WANDB_MODE is left unset: villa then initialises wandb as disabled and nothing is sent anywhere.
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:?usage: run_fit.sh recipe|reduced|smoke [STEPS]}
case "$ARM" in
  recipe) [ $# -eq 1 ] || { echo "the recipe arm takes no step count" >&2; exit 2; }; STEPS=30000 ;;
  reduced|smoke) STEPS=${2:?"$ARM needs a step count"} ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac
OUT=$R/work/fit_$ARM
if [ -e "$OUT" ] && [ -z "${FIT_SPIRAL_RESUME_PATH:-}" ]; then
  echo "$OUT exists: an arm is run once; move it aside or resume it explicitly" >&2; exit 2
fi
mkdir -p "$OUT" "$R/work/cache"
# No FIT_SPIRAL_RUN_TAG: villa appends the tag to every winding folder (w047_TAG), and the published
# windings carry plain names.
export FIT_SPIRAL_OUT_DIR=$OUT
unset FIT_SPIRAL_RUN_TAG
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FIT_SPIRAL_CONFIG_OVERRIDES=$("$PY" -I -c '
import json, sys
print(json.dumps({
    "z_begin": 9500, "z_end": 11000, "input_disable_patches": True,
    "loss_weight_shell_outer": 0, "loss_weight_shell_patch_radius": 0,
    "dense_spacing_mode": "phase", "optimizer_num_training_steps": int(sys.argv[1]),
}))' "$STEPS")
export FIT_SPIRAL_CONFIG_OVERRIDES
unset WANDB_MODE
cd "$SPIRAL" || exit 2
echo "FIT_START $(date -Is) arm=$ARM steps=$STEPS overrides=$FIT_SPIRAL_CONFIG_OVERRIDES"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 \
  > "$R/logs/fit_${ARM}_gpu.csv" &
SMI=$!
t0=$(date +%s)
/usr/bin/time -v "$PY" fit_spiral.py --dataset "$R/dataset" --cache "$R/work/cache"
rc=$?
kill "$SMI" 2>/dev/null
PEAK=$(cut -d, -f2 "$R/logs/fit_${ARM}_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
gate "$ARM" fit "$rc" "$(( $(date +%s) - t0 ))" "\"steps\": $STEPS, \"gpu_peak_mib_all_processes\": ${PEAK:-null}"
echo "FIT_GPU_PEAK_MIB $PEAK"
echo "FIT_EXIT $rc $(date -Is)"
exit $rc
