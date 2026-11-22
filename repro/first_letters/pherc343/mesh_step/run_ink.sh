#!/usr/bin/env bash
# The four released ink models on one winding's render, at one depth, both sides: the recipe's
# run_depth_sweep.sh unchanged, with the kill test's checkpoints and environment.
#
# usage: run_ink.sh ARM WINDING [DEPTH]      DEPTH defaults to +1, the depth the published image shows
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:?usage: run_ink.sh ARM WINDING [DEPTH]}; W=${2:?usage: run_ink.sh ARM WINDING [DEPTH]}; D=${3:-1}
RENDER=$R/work/render_$ARM/${W}_66.zarr
OUT=$R/work/maps_$ARM/$W
[ -d "$RENDER/2" ] || { echo "no render at $RENDER" >&2; exit 2; }
mkdir -p "$R/work/tmp" "$OUT"
echo "INK_START $(date -Is) arm=$ARM winding=$W depth=$D"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 \
  > "$R/logs/ink_${ARM}_${W}_gpu.csv" &
SMI=$!
t0=$(date +%s)
env -u PYTHONPATH CKPT_DIR="$B/ckpt" PY="$B/venv/bin/python" TMPDIR="$R/work/tmp" PYTHONNOUSERSITE=1 \
  P_VILLA=1 P_HEC=1 bash "$RECIPE/ink/scripts/run_depth_sweep.sh" "$RENDER" "$OUT" "$D" "$D"
rc=$?
kill "$SMI" 2>/dev/null
N=$(find "$OUT" -maxdepth 1 \( -name "${W}_66__*.tif" -o -name "${W}_66__*.png" \) | wc -l)
if [ $rc -eq 0 ] && [ "$N" -lt 8 ]; then echo "only $N of 8 maps in $OUT" >&2; rc=1; fi
PEAK=$(cut -d, -f2 "$R/logs/ink_${ARM}_${W}_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
[ "$D" = 1 ] && gate "$ARM" "ink_$W" "$rc" "$(( $(date +%s) - t0 ))" "\"gpu_peak_mib_all_processes\": ${PEAK:-null}"
echo "INK_EXIT $rc $(date -Is)"
exit $rc
