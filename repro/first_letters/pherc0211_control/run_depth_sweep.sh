#!/usr/bin/env bash
# Finding 135: at what depth does Studio read our geometry best, where PHerc. 211's First Letters prize was won?
# Registration: docs/preregistration/2026-11-22_studio_depth_sweep.md. Runs once, unattended, each step only if the
# one before exited 0. Nothing is fitted, snapped, flattened or rendered: every map comes from a render on disk.
#   check      finding 123's weights and the winner's inference.py against their SHA-256 values
#   sweep211   per arm (e2e: finding 121's windings; dense2s3: finding 134's), winding and shift D other than 0:
#              depth_sweep.py planes (layers 41+D down to 26+D of the 66-layer render), then Studio with the winner's
#              command, as finding 124 ran it
#   sweep343   the same for the recipe's PHerc. 343 surface (finding 110's render)
#   repeat     Studio again on finding 124's own planes of w035 (D = 0): is the map the same? (described)
#   compare    depth_sweep.py compare (registered) and compare343 (described)
# Gates: C/work/gate/depth_sweep_<step>.json. Studio's weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_depth_sweep.sh
set -u
export FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"  # the band's env (R, gate) and finding 118's (C, WINNER, SEG, RENDER, MAPS)
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
ENV=$C/work/studio_env
WEIGHTS=$C/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$WINNER/v9/inference
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
OUT=$C/work/depth_sweep
SHIFTS=(-8 -6 -4 -2 -1 1 2 4 6 8)  # and 0, which is finding 124's, 134's and 127's maps
WINDINGS=(w033 w034 w035 w036)
B343=$FL_ROOT/pherc343_repro/work
N343=concat_w047-w048_R5B2_z9500-11000
declare -A FINALS=([e2e]=$R/work/final_e2e [dense2s3]=$R/work/final_e2e_dense2s3)
declare -A RENDERS=([e2e]=$R/work/render_e2e [dense2s3]=$R/work/render_e2e_dense2s3)
declare -A ZERO=([e2e]=$C/work/studio_e2e/maps [dense2s3]=$C/work/snap_passes/maps/e2e_dense2s3)
[ -e "$OUT" ] && { echo "$OUT exists: finding 135 runs once" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's Studio environment is missing" >&2; exit 2; }
for arm in e2e dense2s3; do
  for w in "${WINDINGS[@]}"; do
    [ -d "${RENDERS[$arm]}/${w}_66.zarr/0" ] && [ -f "${ZERO[$arm]}/$w.npy" ] && [ -f "${ZERO[$arm]}/${w}_reversed.npy" ] \
      || { echo "$arm $w: render or D = 0 maps missing" >&2; exit 2; }
  done
done
[ -d "$B343/${N343}_66.zarr/0" ] && [ -f "$B343/studio_343/maps/forward.npy" ] \
  || { echo "finding 110's render or finding 127's maps are missing" >&2; exit 2; }
mkdir -p "$OUT/planes" "$OUT/logs" "$C/work/gate"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$OUT/logs/$name.log" 2>&1
  rc=$?
  control_gate "depth_sweep_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

studio() {  # PLANES MAP: the winner's command, as finding 124
  (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
     --input "$1" --output "$2" --checkpoint "$WEIGHTS" --stride 64 --blend hann --batch-size 32) || return 1
  rm -f "$1"
}

one() {  # RENDER SHIFT MAP
  local planes
  planes=$OUT/planes/$(basename "$3")
  echo "shift $2 $1 $(date -Is)"
  "$PYW" -I "$HERE/depth_sweep.py" planes "$1" "$planes" --shift "$2" || return 1
  studio "$planes" "$3"
}

sweep211() {
  local arm d w dir
  for arm in e2e dense2s3; do
    for d in "${SHIFTS[@]}"; do
      dir=$OUT/maps/$arm/$(printf 'd%+d' "$d")
      mkdir -p "$dir"
      for w in "${WINDINGS[@]}"; do
        one "${RENDERS[$arm]}/${w}_66.zarr" "$d" "$dir/$w.npy" || return 1
      done
    done
  done
}

sweep343() {
  local d dir
  for d in "${SHIFTS[@]}"; do
    dir=$OUT/maps/343/$(printf 'd%+d' "$d")
    mkdir -p "$dir"
    one "$B343/${N343}_66.zarr" "$d" "$dir/forward.npy" || return 1
  done
}

repeat() {  # Studio twice on the same input: finding 124's w035 planes again, and the largest difference
  mkdir -p "$OUT/repeat"
  "$PYW" -I "$HERE/studio_e2e.py" planes "${RENDERS[e2e]}/w035_66.zarr" "$OUT/planes/repeat_w035.npy" || return 1
  studio "$OUT/planes/repeat_w035.npy" "$OUT/repeat/w035.npy" || return 1
  "$PYW" -I -c "import json, sys, numpy as np
a = np.load(sys.argv[1]); b = np.load(sys.argv[2])
print(json.dumps({'max_abs_difference': float(np.abs(a - b).max()), 'identical': bool((a == b).all())}))" \
    "$OUT/repeat/w035.npy" "${ZERO[e2e]}/w035.npy" > "$OUT/repeat.json" || return 1
  cat "$OUT/repeat.json"
}

compare() {
  "$PYW" -I "$HERE/depth_sweep.py" compare "$C/work/depth_sweep.json" \
    --winner-mesh "$SEG" --winner-maps "$MAPS" --winner-render "$RENDER" \
    --studio "$WINNER/download/v9_studiosoft_probability_f32.tif" --studio-mask "$WINNER/v9/studiosoft-mask.png" \
    --ours-render-map "$C/work/studio_e2e/maps/v9.npy" --windings "${WINDINGS[@]}" \
    --arm e2e "${FINALS[e2e]}" "${RENDERS[e2e]}" "${ZERO[e2e]}" "$OUT/maps/e2e" \
    --arm dense2s3 "${FINALS[dense2s3]}" "${RENDERS[dense2s3]}" "${ZERO[dense2s3]}" "$OUT/maps/dense2s3" \
    --sdt "$(ls -d "$R"/work/surf_sdt/*_surf_sdt.ome.zarr | head -1)"
  local rc=$?
  "$PYW" -I "$HERE/depth_sweep.py" compare343 "$C/work/depth_sweep_343.json" --render "$B343/${N343}_66.zarr" \
    --sidecar "$B343/studio_343/reference/$N343.json" --ink-png "$B343/studio_343/reference/${N343}_ink.png" \
    --zero "$B343/studio_343/maps/forward.npy" --zero-reversed "$B343/studio_343/maps/reversed.npy" \
    --sweep "$OUT/maps/343" || return 1
  return $rc
}

step check bash -c "printf '%s  %s\n%s  %s\n' '$W_SHA' '$WEIGHTS' '$CODE_SHA' '$CODE/inference.py' | sha256sum -c"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 > "$OUT/gpu.csv" &
SMI=$!
step sweep211 sweep211
step sweep343 sweep343
step repeat repeat
kill "$SMI" 2>/dev/null
peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
step compare compare
tail -40 "$OUT/logs/compare.log"
