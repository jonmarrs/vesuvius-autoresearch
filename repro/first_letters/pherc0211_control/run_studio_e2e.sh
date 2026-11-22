#!/usr/bin/env bash
# Finding 124: Studio reading our own geometry at the place where PHerc. 211's First Letters prize was won.
# Registration: docs/preregistration/2026-11-16_first_letters_0211_studio_e2e.md. Each step only if the one before
# exited 0:
#   check    finding 123's weights and the winner's inference.py against the winner's SHA-256 values
#   planes   studio_e2e.py planes: finding 118's render of the winner's surface, and finding 121's four windings
#            in Studio's order and reversed (the other side)
#   infer    the winner's inference.py with the winner's command, in finding 123's environment, on each
#   compare  studio_e2e.py compare
# The weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_studio_e2e.sh
set -u
export FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"  # the band's R and finding 118's C, WINNER, SEG, RENDER, MAPS
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
ENV=$C/work/studio_env
WEIGHTS=$C/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$WINNER/v9/inference
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
OUT=$C/work/studio_e2e
WINDINGS=(w033 w034 w035 w036)
[ -e "$OUT" ] && { echo "$OUT exists: finding 124 runs once" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's environment is missing" >&2; exit 2; }
for w in "${WINDINGS[@]}"; do
  [ -d "$R/work/render_e2e/${w}_66.zarr/0" ] && [ -d "$R/work/maps_e2e/$w" ] || { echo "finding 121's $w is missing" >&2; exit 2; }
done
mkdir -p "$C/logs" "$OUT/planes" "$OUT/maps"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$C/logs/studio_e2e_$name.log" 2>&1
  rc=$?
  control_gate "studio_e2e_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

planes() {
  "$PYW" -I "$HERE/studio_e2e.py" planes "$RENDER" "$OUT/planes/v9.npy" || return 1
  for w in "${WINDINGS[@]}"; do
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_e2e/${w}_66.zarr" "$OUT/planes/$w.npy" || return 1
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_e2e/${w}_66.zarr" "$OUT/planes/${w}_reversed.npy" --reverse || return 1
  done
}

infer() {
  local smi rc=0 peak name
  nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 2 > "$OUT/gpu.csv" &
  smi=$!
  for input in "$OUT"/planes/*.npy; do
    name=$(basename "$input" .npy)
    echo "infer $name $(date -Is)"
    (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
       --input "$input" --output "$OUT/maps/$name.npy" --checkpoint "$WEIGHTS" --stride 64 --blend hann --batch-size 32) || { rc=1; break; }
  done
  kill "$smi" 2>/dev/null
  peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
  printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
  return $rc
}

OURS=()
for w in "${WINDINGS[@]}"; do
  OURS+=(--ours-flipped "$R/work/final_e2e/$w.tifxyz" "$R/work/maps_e2e/$w" "$R/work/render_e2e/${w}_66.zarr" \
         "$OUT/maps/$w.npy" "$OUT/maps/${w}_reversed.npy")
done

step check bash -c "printf '%s  %s\n%s  %s\n' '$W_SHA' '$WEIGHTS' '$CODE_SHA' '$CODE/inference.py' | sha256sum -c"
step planes planes
step infer infer
step compare "$PYW" -I "$HERE/studio_e2e.py" compare "$C/work/studio_e2e.json" \
  --winner-mesh "$SEG" --winner-maps "$MAPS" --winner-render "$RENDER" \
  --studio "$WINNER/download/v9_studiosoft_probability_f32.tif" --studio-mask "$WINNER/v9/studiosoft-mask.png" \
  --ours-render-map "$OUT/maps/v9.npy" "${OURS[@]}" --image "$C/work/studio_e2e_v9.png"
cat "$C/logs/studio_e2e_compare.log"
