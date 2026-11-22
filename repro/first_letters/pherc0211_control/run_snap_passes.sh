#!/usr/bin/env bash
# Finding 134: does a three-pass snap read better than one pass, where PHerc. 211's First Letters prize was won?
# Registration: docs/preregistration/2026-11-20_first_letters_0211_snap_passes.md. Runs once, unattended, after
# finding 131, each step only if the one before exited 0. One new arm of finding 119's windings w033 to w036:
#   e2e_dense2s3  finding 131's densified windings (its arm e2e_dense2, densify_winding.py --factor 2), snapped
#                 three times (run_snap.sh, FL_SNAP_PASSES=3), then finding 121's steps
# Steps:
#   check      finding 123's weights and the winner's inference.py against their SHA-256 values; finding 131's arms
#   prepare    the arm's winding list, and its raw windings: finding 131's densified ones
#   snap       three passes (run_snap.sh)
#   flatten    lasagna, per winding (run_flatten.sh)
#   orient     end_to_end.py orient against the winner's surface (finding 121's rule)
#   render     66 layers, flipped where orient says (run_render.sh)
#   studio     planes 41 down to 26 and reversed, Studio with the winner's command
#   compare    snap_passes_read.py compare: finding 124's windings, finding 131's rerun and dense2, and this arm
# Described: whether the first of the three passes equals finding 131's one-pass snap byte for byte.
# Gates: C/work/gate/snap_passes_<step>.json. Studio's weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_snap_passes.sh
set -u
export FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150
HERE=$(cd "$(dirname "$0")" && pwd)
BAND=$(cd "$HERE/../eligible_band" && pwd)
. "$HERE/env.sh"  # the band's env (R, gate, fit_meshes) and finding 118's (C, WINNER, SEG, RENDER, MAPS)
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
ENV=$C/work/studio_env
WEIGHTS=$C/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$WINNER/v9/inference
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
OUT=$C/work/snap_passes
ARM=e2e_dense2s3
D131=$C/work/dense_read  # finding 131's run
WINDINGS=(w033 w034 w035 w036)
[ -e "$OUT" ] && { echo "$OUT exists: finding 134 runs once" >&2; exit 2; }
[ -e "$R/work/windings_$ARM.txt" ] && { echo "$R/work/windings_$ARM.txt exists: finding 134 runs once" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's Studio environment is missing" >&2; exit 2; }
for w in "${WINDINGS[@]}"; do
  for a in e2e_rerun e2e_dense2; do
    [ -f "$R/work/final_$a/$w.tifxyz/x.tif" ] && [ -f "$D131/maps/$a/$w.npy" ] && [ -f "$D131/maps/$a/${w}_reversed.npy" ] \
      || { echo "finding 131's $a $w is missing" >&2; exit 2; }
  done
  [ -f "$R/work/fit_e2e_dense2/densified/meshes/fitted/$w/x.tif" ] || { echo "finding 131's densified $w is missing" >&2; exit 2; }
done
mkdir -p "$OUT/planes" "$C/logs" "$R/logs"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$C/logs/snap_passes_$name.log" 2>&1
  rc=$?
  control_gate "snap_passes_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

prepare() {
  printf '%s\n' "${WINDINGS[@]}" > "$R/work/windings_$ARM.txt"
  ln -sfn fit_e2e_dense2 "$R/work/fit_$ARM"  # finding 131's densified windings, read under this arm's name
}

orient_arm() {
  local finals=()
  for w in "${WINDINGS[@]}"; do finals+=("$R/work/final_$ARM/$w.tifxyz"); done
  "$PYW" -I "$HERE/end_to_end.py" orient "$OUT/orient_$ARM.json" "$SEG" "${finals[@]}"  # step() logs "wNNN.tifxyz flip"
}

render_arm() {  # each winding flipped or kept as orient decided
  local how
  for w in "${WINDINGS[@]}"; do
    how=$(awk -v n="$w.tifxyz" '$1 == n {print $2}' "$C/logs/snap_passes_orient.log")
    case "$how" in
      flip) bash "$BAND/run_render.sh" "$ARM" "$w" flip || return 1 ;;
      keep) bash "$BAND/run_render.sh" "$ARM" "$w" || return 1 ;;
      *) echo "no orientation for $w" >&2; return 2 ;;
    esac
  done
}

studio_arm() {  # planes in both orders, Studio with the winner's command, planes deleted after
  local w input name
  mkdir -p "$OUT/maps/$ARM"
  for w in "${WINDINGS[@]}"; do
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_$ARM/${w}_66.zarr" "$OUT/planes/$w.npy" || return 1
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_$ARM/${w}_66.zarr" "$OUT/planes/${w}_reversed.npy" --reverse || return 1
    for input in "$OUT/planes/$w.npy" "$OUT/planes/${w}_reversed.npy"; do
      name=$(basename "$input" .npy)
      (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
         --input "$input" --output "$OUT/maps/$ARM/$name.npy" --checkpoint "$WEIGHTS" --stride 64 --blend hann \
         --batch-size 32) || return 1
      rm -f "$input"
    done
  done
}

nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 > "$OUT/gpu.csv" &
SMI=$!  # GPU memory, sampled while the run lasts
trap 'kill "$SMI" 2>/dev/null' EXIT
step check bash -c "printf '%s  %s\n%s  %s\n' '$W_SHA' '$WEIGHTS' '$CODE_SHA' '$CODE/inference.py' | sha256sum -c"
step prepare prepare
step snap env FL_SNAP_PASSES=3 bash "$BAND/run_snap.sh" "$ARM"
for w in "${WINDINGS[@]}"; do step "flatten_$w" bash "$BAND/run_flatten.sh" "$ARM" "$w"; done
for w in "${WINDINGS[@]}"; do  # described: is the first pass finding 131's one-pass snap?
  same=yes
  for f in x y z; do cmp -s "$R/work/snap_$ARM.pass1/$w/$f.tif" "$R/work/snap_e2e_dense2/$w/$f.tif" || same=no; done
  echo "$w $same"
done > "$OUT/pass1_same_as_finding_131.txt"
step orient orient_arm
step render render_arm
step studio studio_arm
step compare "$PYW" -I "$HERE/snap_passes_read.py" compare "$C/work/snap_passes.json" \
  --winner-mesh "$SEG" --winner-maps "$MAPS" --winner-render "$RENDER" \
  --studio "$WINNER/download/v9_studiosoft_probability_f32.tif" --studio-mask "$WINNER/v9/studiosoft-mask.png" \
  --ours-render-map "$C/work/studio_e2e/maps/v9.npy" --windings "${WINDINGS[@]}" \
  --arm f124 "$R/work/final_e2e" "$R/work/render_e2e" "$C/work/studio_e2e/maps" \
  --arm rerun "$R/work/final_e2e_rerun" "$R/work/render_e2e_rerun" "$D131/maps/e2e_rerun" \
  --arm dense2 "$R/work/final_e2e_dense2" "$R/work/render_e2e_dense2" "$D131/maps/e2e_dense2" \
  --arm dense2s3 "$R/work/final_$ARM" "$R/work/render_$ARM" "$OUT/maps/$ARM" \
  --sdt "$(ls -d "$R"/work/surf_sdt/*_surf_sdt.ome.zarr | head -1)"
kill "$SMI" 2>/dev/null
peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
tail -20 "$C/logs/snap_passes_compare.log"
