#!/usr/bin/env bash
# villa fit_spiral on the chosen scroll's band with the PHerc. 343 recipe's overrides and villa's defaults for
# everything else (130 windings, 16 voxels a winding to start, seed 1).
#
# usage: run_fit.sh ARM [STEPS]
#   ARM    full    the registered fit: 30,000 steps
#          smoke   a few hundred steps: builds the pools, shows memory and time, and gives the floor of the
#                  sheet-following score (an unconverged fit)
#   STEPS  required for smoke; refused for full
#
# Writes R/work/fit_ARM/ (villa's own layout below it), R/logs/fit_ARM.log and a GPU-memory trace.
# WANDB_MODE is left unset: villa then initialises wandb as disabled and nothing is sent anywhere.
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:?usage: run_fit.sh full|smoke [STEPS]}
case "$ARM" in
  full) [ $# -eq 1 ] || { echo "the full arm takes no step count" >&2; exit 2; }; STEPS=30000 ;;
  smoke) STEPS=${2:?"smoke needs a step count"} ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac
OUT=$R/work/fit_$ARM
[ -e "$OUT" ] && { echo "$OUT exists: an arm is run once" >&2; exit 2; }
[ -s "$R/dataset/spiral-scroll.json" ] || { echo "no dataset: run setup/make_dataset.sh" >&2; exit 2; }
mkdir -p "$OUT" "$R/work/cache"
export FIT_SPIRAL_OUT_DIR=$OUT
unset FIT_SPIRAL_RUN_TAG WANDB_MODE
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FIT_SPIRAL_CONFIG_OVERRIDES=$("$PY" -I -c '
import json, sys
print(json.dumps({
    "z_begin": int(sys.argv[1]), "z_end": int(sys.argv[2]), "input_disable_patches": True,
    "loss_weight_shell_outer": 0, "loss_weight_shell_patch_radius": 0,
    "dense_spacing_mode": "phase", "optimizer_num_training_steps": int(sys.argv[3]),
}))' "$Z_BEGIN" "$Z_END" "$STEPS")
export FIT_SPIRAL_CONFIG_OVERRIDES
cd "$SPIRAL" || exit 2
echo "FIT_START $(date -Is) scroll=$SCROLL sense=$SENSE arm=$ARM steps=$STEPS overrides=$FIT_SPIRAL_CONFIG_OVERRIDES"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 \
  > "$R/logs/fit_${ARM}_gpu.csv" &
SMI=$!
t0=$(date +%s)
/usr/bin/time -v "$PY" fit_spiral.py --dataset "$R/dataset" --cache "$R/work/cache"
rc=$?
kill "$SMI" 2>/dev/null
PEAK=$(cut -d, -f2 "$R/logs/fit_${ARM}_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
gate "$ARM" fit "$rc" "$(( $(date +%s) - t0 ))" "\"steps\": $STEPS, \"gpu_peak_mib_all_processes\": ${PEAK:-null}"
echo "FIT_EXIT $rc $(date -Is)"
exit $rc
