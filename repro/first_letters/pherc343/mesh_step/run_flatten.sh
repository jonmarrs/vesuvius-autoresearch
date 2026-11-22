#!/usr/bin/env bash
# Step 4 of the recipe's mesh step: villa's lasagna flattening of one snapped winding, with villa's own
# configs/flatten_fast_nofilter.json at 0fb38c45 (the config the published meshes record in meta.json).
# GPU. The flattened winding is linked as R/work/final_ARM/WINDING.tifxyz.
#
# usage: run_flatten.sh ARM WINDING
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:?usage: run_flatten.sh ARM WINDING}; W=${2:?usage: run_flatten.sh ARM WINDING}
IN=$R/work/snap_$ARM/$W
OUT=$R/work/flatten_$ARM/$W
[ -f "$IN/x.tif" ] || { echo "no snapped winding at $IN" >&2; exit 2; }
[ -e "$OUT" ] && { echo "$OUT exists: a step is run once per arm" >&2; exit 2; }
[ "$(git -C "$V" rev-parse HEAD)" = "$VILLA_SHA" ] || { echo "$V is not at villa $VILLA_SHA" >&2; exit 2; }
[ -z "$(git -C "$V" status --porcelain -- lasagna vesuvius/src)" ] || { echo "$V has local changes" >&2; exit 2; }
mkdir -p "$OUT"
printf '{"external_surfaces": [{"path": "%s"}]}\n' "$IN" > "$OUT/flatten_input.json"
echo "FLATTEN_START $(date -Is) arm=$ARM winding=$W"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 \
  > "$R/logs/flatten_${ARM}_${W}_gpu.csv" &
SMI=$!
t0=$(date +%s)
( cd "$V/lasagna" && PYTHONPATH=$V/vesuvius/src PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /usr/bin/time -v "$PY" fit.py "$V/lasagna/configs/flatten_fast_nofilter.json" "$OUT/flatten_input.json" \
    --out-dir "$OUT" --device cuda )
rc=$?
kill "$SMI" 2>/dev/null
RESULT=$OUT/tifxyz/flatten.tifxyz
if [ $rc -eq 0 ] && [ ! -f "$RESULT/x.tif" ]; then echo "no flattened mesh at $RESULT" >&2; rc=1; fi
if [ $rc -eq 0 ]; then mkdir -p "$R/work/final_$ARM" && ln -sfn "$RESULT" "$R/work/final_$ARM/$W.tifxyz"; fi
PEAK=$(cut -d, -f2 "$R/logs/flatten_${ARM}_${W}_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
gate "$ARM" "flatten_$W" "$rc" "$(( $(date +%s) - t0 ))" "\"gpu_peak_mib_all_processes\": ${PEAK:-null}"
echo "FLATTEN_EXIT $rc $(date -Is)"
exit $rc
