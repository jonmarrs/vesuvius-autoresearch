#!/usr/bin/env bash
# The winding direction is not published for PHerc. 0125, so it is measured: the same short fit with the
# spiral declared CW and ACW, compared on the track loss. Run on PHerc. 343 first, where CW is known.
#
# usage: run_sense.sh ENV_SH Z_BEGIN Z_END SENSE STEPS
#   ENV_SH   env.sh of the scroll (this directory's, or ../pherc343/mesh_step/env.sh); it gives R, SPIRAL, PY
# Reads R/dataset (spiral-scroll.json, umbilicus, tracks); writes R/work/sense_SENSE_STEPS/ with a copy of the
# dataset description that differs only in spiral_outward_sense, and R/logs/sense_SENSE_STEPS.log.
set -u
ENV=${1:?ENV_SH}; ZB=${2:?Z_BEGIN}; ZE=${3:?Z_END}; SENSE=${4:?CW|ACW}; STEPS=${5:?STEPS}
. "$ENV"
case "$SENSE" in CW|ACW) ;; *) echo "sense is CW or ACW" >&2; exit 2 ;; esac
OUT=$R/work/sense_${SENSE}_$STEPS
[ -e "$OUT" ] && { echo "$OUT exists: a trial is run once" >&2; exit 2; }
mkdir -p "$OUT/dataset" "$R/work/cache"
ln -s "$R/dataset/tracks" "$OUT/dataset/tracks"
cp "$R/dataset/umbilicus.json" "$OUT/dataset/umbilicus.json"
"$PY" -I -c '
import json, sys
spec = json.load(open(sys.argv[1]))
spec["spiral_outward_sense"] = sys.argv[3]
json.dump(spec, open(sys.argv[2], "w"), indent=2)' "$R/dataset/spiral-scroll.json" "$OUT/dataset/spiral-scroll.json" "$SENSE"
export FIT_SPIRAL_OUT_DIR=$OUT/fit
unset FIT_SPIRAL_RUN_TAG WANDB_MODE
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FIT_SPIRAL_CONFIG_OVERRIDES=$("$PY" -I -c '
import json, sys
print(json.dumps({
    "z_begin": int(sys.argv[1]), "z_end": int(sys.argv[2]), "input_disable_patches": True,
    "loss_weight_shell_outer": 0, "loss_weight_shell_patch_radius": 0,
    "dense_spacing_mode": "phase", "optimizer_num_training_steps": int(sys.argv[3]),
}))' "$ZB" "$ZE" "$STEPS")
export FIT_SPIRAL_CONFIG_OVERRIDES
cd "$SPIRAL" || exit 2
echo "SENSE_START $(date -Is) sense=$SENSE steps=$STEPS overrides=$FIT_SPIRAL_CONFIG_OVERRIDES"
/usr/bin/time -v "$PY" fit_spiral.py --dataset "$OUT/dataset" --cache "$R/work/cache"
rc=$?
echo "SENSE_EXIT $rc $(date -Is)"
exit $rc
