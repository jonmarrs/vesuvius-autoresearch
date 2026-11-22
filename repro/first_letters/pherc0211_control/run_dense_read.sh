#!/usr/bin/env bash
# Finding 131: does the twice-denser snap read better at the place where PHerc. 211's First Letters prize was won?
# Registration: docs/preregistration/2026-11-20_first_letters_0211_dense_read.md. Runs once, unattended, each step
# only if the one before exited 0. Two arms of finding 119's windings w033 to w036, each through finding 121's steps:
#   e2e_rerun    the raw windings as they are (finding 121's route again: its run-to-run noise)
#   e2e_dense2   the raw windings subdivided twice first (densify_winding.py --factor 2, finding 130)
# Steps:
#   check      finding 123's weights and the winner's inference.py against their SHA-256 values
#   prepare    each arm's winding list and raw windings
#   snap       the recipe's snap, per arm (run_snap.sh)
#   flatten    lasagna, per arm and winding (run_flatten.sh)
#   orient     end_to_end.py orient against the winner's surface, per arm (finding 121's rule)
#   render     66 layers, flipped where orient says (run_render.sh)
#   studio     planes 41 down to 26 and reversed, Studio with the winner's command, per arm and winding
#   compare    dense_read.py compare, with finding 124's windings and maps as the third arm
# Gates: C/work/gate/dense_read_<step>.json. Studio's weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_dense_read.sh
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
OUT=$C/work/dense_read
ARMS=(e2e_rerun e2e_dense2)
WINDINGS=(w033 w034 w035 w036)
[ -e "$OUT" ] && { echo "$OUT exists: finding 131 runs once" >&2; exit 2; }
for arm in "${ARMS[@]}"; do
  [ -e "$R/work/windings_$arm.txt" ] && { echo "$R/work/windings_$arm.txt exists: finding 131 runs once" >&2; exit 2; }
done
[ -x "$ENV/bin/python" ] || { echo "finding 123's Studio environment is missing" >&2; exit 2; }
for w in "${WINDINGS[@]}"; do
  [ -f "$R/work/final_e2e/$w.tifxyz/x.tif" ] && [ -f "$C/work/studio_e2e/maps/$w.npy" ] \
    || { echo "finding 121's or 124's $w is missing" >&2; exit 2; }
done
mkdir -p "$OUT/planes" "$C/logs" "$R/logs"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$C/logs/dense_read_$name.log" 2>&1
  rc=$?
  control_gate "dense_read_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

prepare() {
  local base dest w
  base=$(fit_meshes full) || return 1
  for arm in "${ARMS[@]}"; do printf '%s\n' "${WINDINGS[@]}" > "$R/work/windings_$arm.txt"; done
  ln -sfn fit_full "$R/work/fit_e2e_rerun"  # finding 119's fit, read under this arm's name, as finding 121 did
  dest=$R/work/fit_e2e_dense2/densified/meshes/fitted
  mkdir -p "$dest"
  for w in "${WINDINGS[@]}"; do
    "$PYW" -I "$BAND/densify_winding.py" "$base/$w" "$dest/$w" --factor 2 || return 1
  done
}

render_arm() {  # ARM: each winding flipped or kept as orient decided
  local how
  for w in "${WINDINGS[@]}"; do
    how=$(awk -v n="$w.tifxyz" '$1 == n {print $2}' "$C/logs/dense_read_orient_$1.log")
    case "$how" in
      flip) bash "$BAND/run_render.sh" "$1" "$w" flip || return 1 ;;
      keep) bash "$BAND/run_render.sh" "$1" "$w" || return 1 ;;
      *) echo "no orientation for $w" >&2; return 2 ;;
    esac
  done
}

orient_arm() {  # ARM
  local finals=()
  for w in "${WINDINGS[@]}"; do finals+=("$R/work/final_$1/$w.tifxyz"); done
  "$PYW" -I "$HERE/end_to_end.py" orient "$OUT/orient_$1.json" "$SEG" "${finals[@]}"  # step() logs "wNNN.tifxyz flip"
}

studio_arm() {  # ARM: planes in both orders, Studio with the winner's command, planes deleted after
  local w input name
  mkdir -p "$OUT/maps/$1"
  for w in "${WINDINGS[@]}"; do
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_$1/${w}_66.zarr" "$OUT/planes/$w.npy" || return 1
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R/work/render_$1/${w}_66.zarr" "$OUT/planes/${w}_reversed.npy" --reverse || return 1
    for input in "$OUT/planes/$w.npy" "$OUT/planes/${w}_reversed.npy"; do
      name=$(basename "$input" .npy)
      (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
         --input "$input" --output "$OUT/maps/$1/$name.npy" --checkpoint "$WEIGHTS" --stride 64 --blend hann \
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
for arm in "${ARMS[@]}"; do step "snap_$arm" bash "$BAND/run_snap.sh" "$arm"; done
for arm in "${ARMS[@]}"; do
  for w in "${WINDINGS[@]}"; do step "flatten_${arm}_$w" bash "$BAND/run_flatten.sh" "$arm" "$w"; done
done
for w in "${WINDINGS[@]}"; do  # described: is finding 121's route byte-for-byte repeatable?
  for stage in snap final; do
    same=yes
    for f in x y z; do
      cmp -s "$R/work/${stage}_e2e_rerun/$w$( [ $stage = final ] && echo .tifxyz )/$f.tif" \
             "$R/work/${stage}_e2e/$w$( [ $stage = final ] && echo .tifxyz )/$f.tif" || same=no
    done
    echo "$w $stage $same"
  done
done > "$OUT/rerun_same_as_finding_121.txt"
for arm in "${ARMS[@]}"; do step "orient_$arm" orient_arm "$arm"; done
for arm in "${ARMS[@]}"; do step "render_$arm" render_arm "$arm"; done
for arm in "${ARMS[@]}"; do step "studio_$arm" studio_arm "$arm"; done
step compare "$PYW" -I "$HERE/dense_read.py" compare "$C/work/dense_read.json" \
  --winner-mesh "$SEG" --winner-maps "$MAPS" --winner-render "$RENDER" \
  --studio "$WINNER/download/v9_studiosoft_probability_f32.tif" --studio-mask "$WINNER/v9/studiosoft-mask.png" \
  --ours-render-map "$C/work/studio_e2e/maps/v9.npy" --windings "${WINDINGS[@]}" \
  --arm f124 "$R/work/final_e2e" "$R/work/render_e2e" "$C/work/studio_e2e/maps" \
  --arm rerun "$R/work/final_e2e_rerun" "$R/work/render_e2e_rerun" "$OUT/maps/e2e_rerun" \
  --arm dense2 "$R/work/final_e2e_dense2" "$R/work/render_e2e_dense2" "$OUT/maps/e2e_dense2" \
  --sdt "$(ls -d "$R"/work/surf_sdt/*_surf_sdt.ome.zarr | head -1)"
kill "$SMI" 2>/dev/null
peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
tail -20 "$C/logs/dense_read_compare.log"
