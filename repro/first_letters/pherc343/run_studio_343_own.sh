#!/usr/bin/env bash
# Finding 136: does Studio draw PHerc. 343's letters on our own fit of the place, as on the recipe's published surface?
# Registration: docs/preregistration/2026-11-22_studio_343_own_windings.md. Runs once, each step only if the one
# before exited 0. Nothing is fitted, snapped, flattened or rendered: the windings and renders are finding 110's.
#   check      finding 123's weights and the winner's inference.py against their SHA-256 values
#   planes     studio_e2e.py planes: layers 41 down to 26 of w047's and w048's 66-layer renders, and reversed
#   infer      the winner's inference.py with the winner's command, in finding 123's environment, on all four
#   compare    studio_343_own.py compare, against finding 127's map of the published surface
# The weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_studio_343_own.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
FL_ROOT=${FL_ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters}
B=$FL_ROOT/pherc343_repro/work
M=$FL_ROOT/pherc343_mesh/work
C=$FL_ROOT/pherc0211_control
N=concat_w047-w048_R5B2_z9500-11000
PYW=${PYW:-$ROOT/.venv/bin/python}
ENV=$C/work/studio_env
WEIGHTS=$C/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$C/inputs/winner/v9/inference
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
WINDINGS=(w047 w048)
OUT=$M/studio_own
[ -e "$OUT" ] && { echo "$OUT exists: finding 136 runs once" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's environment is missing" >&2; exit 2; }
for w in "${WINDINGS[@]}"; do
  [ -d "$M/render_recipe/${w}_66.zarr/0" ] && [ -d "$M/final_recipe/$w.tifxyz" ] \
    || { echo "finding 110's $w render or mesh is missing" >&2; exit 2; }
done
[ -f "$B/studio_343/maps/forward.npy" ] && [ -f "$B/studio_343/maps/reversed.npy" ] \
  || { echo "finding 127's maps are missing" >&2; exit 2; }
mkdir -p "$OUT/planes" "$OUT/maps" "$OUT/logs" "$OUT/gate"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$OUT/logs/$name.log" 2>&1
  rc=$?
  printf '{"exit": %d, "seconds": %d}\n' "$rc" "$(( $(date +%s) - t0 ))" > "$OUT/gate/$name.json"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

planes() {
  local w
  for w in "${WINDINGS[@]}"; do
    "$PYW" -I "$ROOT/repro/first_letters/pherc0211_control/studio_e2e.py" planes "$M/render_recipe/${w}_66.zarr" \
      "$OUT/planes/$w.npy" || return 1
    "$PYW" -I "$ROOT/repro/first_letters/pherc0211_control/studio_e2e.py" planes "$M/render_recipe/${w}_66.zarr" \
      "$OUT/planes/${w}_reversed.npy" --reverse || return 1
  done
}

infer() {
  local smi rc=0 peak name
  nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 2 > "$OUT/gpu.csv" &
  smi=$!
  for name in w047 w047_reversed w048 w048_reversed; do
    echo "infer $name $(date -Is)"
    (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
       --input "$OUT/planes/$name.npy" --output "$OUT/maps/$name.npy" --checkpoint "$WEIGHTS" --stride 64 \
       --blend hann --batch-size 32) || { rc=1; break; }
    rm -f "$OUT/planes/$name.npy"
  done
  kill "$smi" 2>/dev/null
  peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
  printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
  return $rc
}

compare() {
  "$PYW" -I "$HERE/studio_343_own.py" compare "$M/studio_own.json" \
    --published-mesh "$B/mesh/$N.tifxyz" --published-render "$B/${N}_66.zarr" \
    --published-studio "$B/studio_343/maps/forward.npy" --published-studio-reversed "$B/studio_343/maps/reversed.npy" \
    --sidecar "$B/studio_343/reference/$N.json" --ink-png "$B/studio_343/reference/${N}_ink.png" \
    --ours "$M/final_recipe/w047.tifxyz" "$M/render_recipe/w047_66.zarr" "$OUT/maps/w047.npy" "$OUT/maps/w047_reversed.npy" \
    --ours "$M/final_recipe/w048.tifxyz" "$M/render_recipe/w048_66.zarr" "$OUT/maps/w048.npy" "$OUT/maps/w048_reversed.npy" \
    --image "$OUT/studio_own.png"
}

step check bash -c "printf '%s  %s\n%s  %s\n' '$W_SHA' '$WEIGHTS' '$CODE_SHA' '$CODE/inference.py' | sha256sum -c"
step planes planes
step infer infer
step compare compare
cat "$OUT/logs/compare.log"
