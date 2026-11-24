#!/usr/bin/env bash
# Finding 137: does a fit declared to turn the wrong way still read the text where PHerc. 211's prize was won?
# Registration: docs/preregistration/2026-11-22_first_letters_0211_wrong_hand_read.md. Runs once, each step only
# if the one before exited 0:
#   check     finding 123's weights and the winner's inference.py against their SHA-256 values; finding 124's
#             maps and finding 121's windings are on disk
#   fit       run_fit.sh full-otherhand: finding 119's fit of band z 7650-9150, only the direction declared
#             clockwise against the catalog's anticlockwise (30,000 steps)
#   choose    wrong_hand.py choose: the four raw windings with the most winner lattice points within 4 voxels
#   snap      the recipe's snap of those windings (one pass, as finding 121)
#   flatten   lasagna, per winding
#   orient    end_to_end.py orient: flip or keep each render, from its normals against the winner's surface
#   render    66 layers per winding, flipped as orient says
#   planes    studio_e2e.py planes: our layers 41 down to 26, and the same reversed (the other-side control)
#   infer     the winner's inference.py with the winner's command, in finding 123's environment
#   compare   wrong_hand.py compare: arm right (finding 124's windings and maps) against arm wrong
# The weights and Studio's outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_wrong_hand.sh
set -u
export FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150
HERE=$(cd "$(dirname "$0")" && pwd)
BAND=$(cd "$HERE/../eligible_band" && pwd)
. "$HERE/env.sh"  # the band's R, fit_meshes and finding 118's C, WINNER, SEG, RENDER, MAPS
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
FIT=full-otherhand
ARM=e2e_otherhand
ENV=$C/work/studio_env
WEIGHTS=$C/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$WINNER/v9/inference
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
RIGHT=(w033 w034 w035 w036)
OUT=$C/work/wrong_hand
[ -e "$OUT" ] && { echo "$OUT exists: finding 137 runs once" >&2; exit 2; }
[ -e "$R/work/fit_$FIT" ] && { echo "$R/work/fit_$FIT exists" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's environment is missing" >&2; exit 2; }
for w in "${RIGHT[@]}"; do
  [ -d "$R/work/final_e2e/$w.tifxyz" ] && [ -d "$R/work/render_e2e/${w}_66.zarr/0" ] \
    && [ -f "$C/work/studio_e2e/maps/$w.npy" ] && [ -f "$C/work/studio_e2e/maps/${w}_reversed.npy" ] \
    || { echo "finding 121's or 124's $w is missing" >&2; exit 2; }
done
[ -f "$C/work/studio_e2e/maps/v9.npy" ] || { echo "finding 124's map of the winner's surface is missing" >&2; exit 2; }
mkdir -p "$OUT/planes" "$OUT/maps" "$OUT/logs" "$OUT/gate"
printf '%s\n' "${RIGHT[@]}" > "$OUT/right_windings.txt"

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

check() {
  printf '%s  %s\n%s  %s\n' "$W_SHA" "$WEIGHTS" "$CODE_SHA" "$CODE/inference.py" | sha256sum -c
}
choose() {
  local meshes
  meshes=$(fit_meshes "$FIT") || return 1
  "$PYW" -I "$HERE/wrong_hand.py" choose "$meshes" "$SEG" "$OUT/choose.json" "$R/work/windings_$ARM.txt"
}
flatten() {
  local w
  for w in "${WINDINGS[@]}"; do bash "$BAND/run_flatten.sh" "$ARM" "$w" || return 1; done
}
orient() {
  local finals=() w
  for w in "${WINDINGS[@]}"; do finals+=("$R/work/final_$ARM/$w.tifxyz"); done
  "$PYW" -I "$HERE/end_to_end.py" orient "$OUT/orient.json" "$SEG" "${finals[@]}"
}
render() {
  local w how
  for w in "${WINDINGS[@]}"; do
    how=$("$PYW" -I -c 'import json, sys; print(json.load(open(sys.argv[1]))[sys.argv[2] + ".tifxyz"]["render"])' \
      "$OUT/orient.json" "$w") || return 1
    case "$how" in
      flip) bash "$BAND/run_render.sh" "$ARM" "$w" flip || return 1 ;;
      keep) bash "$BAND/run_render.sh" "$ARM" "$w" || return 1 ;;
      *) echo "no orientation for $w" >&2; return 2 ;;
    esac
  done
}
planes() {
  local w
  for w in "${WINDINGS[@]}"; do
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_$ARM/${w}_66.zarr" "$OUT/planes/$w.npy" || return 1
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_$ARM/${w}_66.zarr" "$OUT/planes/${w}_reversed.npy" \
      --reverse || return 1
  done
}
infer() {
  local smi rc=0 peak name w
  nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 2 > "$OUT/gpu.csv" &
  smi=$!
  for w in "${WINDINGS[@]}"; do
    for name in "$w" "${w}_reversed"; do
      echo "infer $name $(date -Is)"
      (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
         --input "$OUT/planes/$name.npy" --output "$OUT/maps/$name.npy" --checkpoint "$WEIGHTS" --stride 64 \
         --blend hann --batch-size 32) || { rc=1; break 2; }
      rm -f "$OUT/planes/$name.npy"
    done
  done
  kill "$smi" 2>/dev/null
  peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
  printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
  return $rc
}

step check check
step fit bash "$BAND/run_fit.sh" "$FIT"
step choose choose
if [ ! -s "$R/work/windings_$ARM.txt" ]; then  # amendment 1: nothing reaches the winner's surface
  step compare "$PYW" -I "$HERE/wrong_hand.py" unreached "$OUT/compare.json" "$OUT/choose.json"
  cat "$OUT/logs/compare.log"
  exit 0
fi
ln -sfn "fit_$FIT" "$R/work/fit_$ARM"  # fit_meshes reads the fit under the read's arm name, as finding 121
mapfile -t WINDINGS < "$R/work/windings_$ARM.txt"
step snap bash "$BAND/run_snap.sh" "$ARM"
step flatten flatten
step orient orient
step render render
step planes planes
step infer infer
step compare "$PYW" -I "$HERE/wrong_hand.py" compare "$OUT/compare.json" \
  --winner-mesh "$SEG" --winner-maps "$MAPS" --winner-render "$RENDER" \
  --studio "$WINNER/download/v9_studiosoft_probability_f32.tif" --studio-mask "$WINNER/v9/studiosoft-mask.png" \
  --ours-render-map "$C/work/studio_e2e/maps/v9.npy" \
  --arm right "$R/work/final_e2e" "$R/work/render_e2e" "$C/work/studio_e2e/maps" - "$OUT/right_windings.txt" \
  --arm wrong "$R/work/final_$ARM" "$R/work/render_$ARM" "$OUT/maps" "$OUT/orient.json" "$R/work/windings_$ARM.txt"
cat "$OUT/logs/compare.log"
