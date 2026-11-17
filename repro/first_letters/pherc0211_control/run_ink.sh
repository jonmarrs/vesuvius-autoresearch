#!/usr/bin/env bash
# Finding 118: the four released ink models of the PHerc. 343 recipe on the render of the winning surface, both
# sides, depths -3 to +2: the recipe's run_depth_sweep.sh unchanged, with the kill test's checkpoints and
# environment, as finding 113 ran it. The maps stay under C.
#
# usage: run_ink.sh
set -u
. "$(dirname "$0")/env.sh"
LO=-3; HI=2
[ -d "$RENDER/2" ] || { echo "no render at $RENDER" >&2; exit 2; }
[ -e "$MAPS" ] && { echo "$MAPS exists: the maps are made once" >&2; exit 2; }
mkdir -p "$C/work/tmp" "$MAPS"
echo "INK_START $(date -Is) surface=$SEG_NAME depths=$LO..$HI"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 \
  > "$C/logs/ink_${SEG_NAME}_gpu.csv" &
SMI=$!
t0=$(date +%s)
env -u PYTHONPATH CKPT_DIR="$B/ckpt" PY="$B/venv/bin/python" TMPDIR="$C/work/tmp" PYTHONNOUSERSITE=1 \
  P_VILLA=1 P_HEC=1 bash "$RECIPE/ink/scripts/run_depth_sweep.sh" "$RENDER" "$MAPS" "$LO" "$HI"
rc=$?
kill "$SMI" 2>/dev/null
NAME=$(basename "$RENDER" .zarr)
WANT=$(( (HI - LO + 1) * 8 ))
N=$(find "$MAPS" -maxdepth 1 \( -name "${NAME}__*.tif" -o -name "${NAME}__*.png" \) | wc -l)
if [ $rc -eq 0 ] && [ "$N" -lt "$WANT" ]; then echo "only $N of $WANT maps in $MAPS" >&2; rc=1; fi
PEAK=$(cut -d, -f2 "$C/logs/ink_${SEG_NAME}_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
control_gate ink "$rc" "$(( $(date +%s) - t0 ))" "\"depths\": [$LO, $HI], \"gpu_peak_mib_all_processes\": ${PEAK:-null}"
echo "INK_EXIT $rc $(date -Is)"
exit $rc
