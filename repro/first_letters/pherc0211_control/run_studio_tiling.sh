#!/usr/bin/env bash
# Finding 128: Studio's published tiling against the winner's, on the winner's own 16-plane input of PHerc. 211.
# Registration: docs/preregistration/2026-11-20_studio_published_tiling.md. Each step only if the one before
# exited 0:
#   check    finding 123's weights, planes and the winner's inference.py against their SHA-256 values
#   infer    inference.py with its default (published) tiling and --batch-size 32, timed
#   compare  studio_tiling.py against finding 123's map, over the winner's mask
# The weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_studio_tiling.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"  # finding 118's C, WINNER
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
V9=$WINNER/v9
IN=$C/inputs/studio
ENV=$C/work/studio_env
OUT=$C/work/studio_tiling
WEIGHTS=$IN/studio-softloss-20261023-ema.safetensors
PLANES=$IN/v9_model_input_planes16_uint8.npy
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
P_SHA=e7cdd509d74958a8cb95e9bfb0b1857610e457363edfe5329850b9b009ff8c22
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
[ -e "$OUT" ] && { echo "$OUT exists: finding 128 runs once" >&2; exit 2; }
[ -s "$C/work/studio_repro/ink.npy" ] || { echo "finding 123's map is missing" >&2; exit 2; }
mkdir -p "$OUT" "$C/logs"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$C/logs/studio_tiling_$name.log" 2>&1
  rc=$?
  control_gate "studio_tiling_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

infer() {
  local smi rc peak
  nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 2 > "$OUT/gpu.csv" &
  smi=$!
  (cd "$V9/inference" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
     --input "$PLANES" --output "$OUT/ink96.npy" --checkpoint "$WEIGHTS" --batch-size 32)
  rc=$?
  kill "$smi" 2>/dev/null
  peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
  echo "gpu_peak_mib_all_processes ${peak:-null}"
  return $rc
}

step check bash -c "printf '%s  %s\n%s  %s\n%s  %s\n' '$W_SHA' '$WEIGHTS' '$P_SHA' '$PLANES' '$CODE_SHA' '$V9/inference/inference.py' | sha256sum -c"
step infer infer
"$PYW" -I "$HERE/studio_tiling.py" "$C/work/studio_tiling.json" "$OUT/ink96.npy" "$C/work/studio_repro/ink.npy" \
  "$V9/studiosoft-mask.png" --gate "$C/work/gate/studio_tiling_infer.json"
