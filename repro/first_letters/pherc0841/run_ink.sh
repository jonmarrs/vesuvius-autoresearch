#!/usr/bin/env bash
# The four released ink models on one segment's render, both sides, at every depth from D_LO to D_HI: the
# recipe's run_depth_sweep.sh unchanged, with the kill test's checkpoints and environment.
#
# usage: run_ink.sh SEGMENT D_LO D_HI
set -u
. "$(dirname "$0")/env.sh"
S=${1:?usage: run_ink.sh SEGMENT D_LO D_HI}; LO=${2:?D_LO}; HI=${3:?D_HI}
NAME=$(segment_name "$S")
RENDER=$R/work/render/${NAME}_66.zarr
OUT=$R/work/maps/$NAME
[ -d "$RENDER/2" ] || { echo "no render at $RENDER" >&2; exit 2; }
mkdir -p "$R/work/tmp" "$OUT"
echo "INK_START $(date -Is) segment=$S depths=$LO..$HI"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 \
  > "$R/logs/ink_${NAME}_gpu.csv" &
SMI=$!
t0=$(date +%s)
env -u PYTHONPATH CKPT_DIR="$B/ckpt" PY="$B/venv/bin/python" TMPDIR="$R/work/tmp" PYTHONNOUSERSITE=1 \
  P_VILLA=1 P_HEC=1 bash "$RECIPE/ink/scripts/run_depth_sweep.sh" "$RENDER" "$OUT" "$LO" "$HI"
rc=$?
kill "$SMI" 2>/dev/null
WANT=$(( (HI - LO + 1) * 8 ))
N=$(find "$OUT" -maxdepth 1 \( -name "${NAME}_66__*.tif" -o -name "${NAME}_66__*.png" \) | wc -l)
if [ $rc -eq 0 ] && [ "$N" -lt "$WANT" ]; then echo "only $N of $WANT maps in $OUT" >&2; rc=1; fi
PEAK=$(cut -d, -f2 "$R/logs/ink_${NAME}_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
gate "ink_$NAME" "$rc" "$(( $(date +%s) - t0 ))" "\"depths\": [$LO, $HI], \"gpu_peak_mib_all_processes\": ${PEAK:-null}"
echo "INK_EXIT $rc $(date -Is)"
exit $rc
