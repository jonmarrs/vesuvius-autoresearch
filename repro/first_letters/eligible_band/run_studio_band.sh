#!/usr/bin/env bash
# Finding 125: Studio reads every raw winding of one fit arm of a band, as images for the owner.
# Registration: docs/preregistration/2026-11-20_first_letters_0826_studio_band.md.
#   snap       the recipe's snap of every raw winding of the arm (run_snap.sh)
#   flatten    lasagna, per winding (run_flatten.sh)
#   orient     studio_band.py orient: flip a winding whose normals point mostly toward the scroll axis
#   render     18 layers per winding (24 to 41 of the 66-layer frame: Studio's 26 to 41 and the surface layer 33,
#              byte-identical to the 66-layer render's; finding 129's amendment 1), flipped as decided (run_render.sh)
#   studio     our layers 41 down to 26 (finding 124's order), Studio with the winner's command (finding 123's
#              environment, weights and inference.py, each checksummed)
#   summarise  studio_band.py summarise: one image per winding, a contact sheet, and numbers
#   stacked    studio_band.py stacked: consecutive snapped windings on one surface (described; finding 126)
# A winding whose flatten, render or Studio step fails is recorded and skipped; the others go on. Studio's weights
# and outputs are CC BY-NC 4.0, and an eligible scroll's outputs stay on this machine.
# STUDIO_WINDINGS=FILE reads only the raw windings it lists (finding 126: those with positive excess).
# STUDIO_TILING=winner (the default: the winner's --stride 64 --blend hann) or published (inference.py's default,
# 96-pixel windows without overlap; finding 128).
# A winding is not rendered while the run directory's disk has less than FL_MIN_FREE_GB free (default 50): its render
# step exits 28, is recorded like any failed step, and nothing is deleted to make room.
#
# usage: FL_SCROLL=PHerc0826 [STUDIO_WINDINGS=FILE] [STUDIO_TILING=winner|published] run_studio_band.sh ARM
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
ARM=${1:?usage: run_studio_band.sh ARM}
CTRL=${FL_CONTROL_DIR:-$FL_ROOT/pherc0211_control}  # finding 123's Studio environment and weights
ENV=$CTRL/work/studio_env
WEIGHTS=$CTRL/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$CTRL/inputs/winner/v9/inference
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
OUT=$R/work/studio_$ARM
SLICES=18  # the centred render that holds Studio's layers 41 to 26 and the surface layer 33 (render_frame.py)
[ -e "$OUT" ] && { echo "$OUT exists: the band is read once per arm" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's Studio environment is missing" >&2; exit 2; }
printf '%s  %s\n%s  %s\n' "$W_SHA" "$WEIGHTS" "$CODE_SHA" "$CODE/inference.py" | sha256sum -c || exit 2
MESHES=$(fit_meshes "$ARM") || exit 2
case "${STUDIO_TILING:-winner}" in
  winner) TILING=(--stride 64 --blend hann) ;;
  published) TILING=() ;;
  *) echo "STUDIO_TILING is winner or published, not '$STUDIO_TILING'" >&2; exit 2 ;;
esac
mkdir -p "$OUT/planes" "$OUT/maps" "$R/logs"

stage() {  # NAME COMMAND...: a band-wide stage; stop the read if it fails
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STAGE_START $name $(date -Is)"
  "$@" > "$R/logs/studio_${ARM}_$name.log" 2>&1
  rc=$?
  gate "$ARM" "studio_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STAGE_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

studio() {  # WINDING FLIP: planes and Studio for one winding
  "$PYW" -I "$ROOT/repro/first_letters/pherc0211_control/studio_e2e.py" planes \
    "$R/work/render_$ARM/${1}_${SLICES}.zarr" "$OUT/planes/$1.npy" || return 1
  (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
     --input "$OUT/planes/$1.npy" --output "$OUT/maps/$1.npy" --checkpoint "$WEIGHTS" "${TILING[@]}" \
     --batch-size 32) || return 1
  rm -f "$OUT/planes/$1.npy"
}

for_each() {  # STEP COMMAND...: per winding; a failure is recorded and the winding is dropped from later steps
  local step=$1 w t0 rc
  shift
  local kept=()
  for w in "${LIVE[@]}"; do
    t0=$(date +%s)
    "$@" "$w" > "$R/logs/studio_${ARM}_${step}_$w.log" 2>&1
    rc=$?
    gate "$ARM" "studio_${step}_$w" "$rc" "$(( $(date +%s) - t0 ))"
    if [ "$rc" -eq 0 ]; then kept+=("$w"); else echo "FAILED $step $w"; fi
  done
  LIVE=("${kept[@]}")
  echo "$step: ${#LIVE[@]} windings go on $(date -Is)"
}

room_for_render() {  # whether the run directory's disk has FL_MIN_FREE_GB (default 50) free
  local avail
  avail=$(df -B1G --output=avail "$R/work" | tail -1 | tr -dc '0-9')
  [ "${avail:-0}" -ge "${FL_MIN_FREE_GB:-50}" ]
}

render_one() {  # WINDING
  local how
  room_for_render || { echo "less than ${FL_MIN_FREE_GB:-50} GB free under $R/work: not rendered" >&2; return 28; }
  how=$(awk -v n="$1" '$1 == n {print $2}' "$R/logs/studio_${ARM}_orient.log")
  case "$how" in
    flip) RENDER_SLICES="$SLICES" bash "$HERE/run_render.sh" "$ARM" "$1" flip ;;
    keep) RENDER_SLICES="$SLICES" bash "$HERE/run_render.sh" "$ARM" "$1" ;;
    *) echo "no orientation for $1" >&2; return 2 ;;
  esac
}

if [ -n "${STUDIO_WINDINGS:-}" ]; then
  ls "$MESHES" | grep -E '^w[0-9]+$' | grep -Fxf "$STUDIO_WINDINGS" > "$R/work/windings_$ARM.txt"
else
  ls "$MESHES" | grep -E '^w[0-9]+$' > "$R/work/windings_$ARM.txt"
fi
[ -s "$R/work/windings_$ARM.txt" ] || { echo "no windings to read" >&2; exit 2; }
mapfile -t LIVE < "$R/work/windings_$ARM.txt"
echo "READ_START $ARM ${#LIVE[@]} windings tiling=${STUDIO_TILING:-winner} $(date -Is)"
stage snap bash "$HERE/run_snap.sh" "$ARM"
stage stacked "$PYW" -I "$HERE/studio_band.py" stacked "$OUT/stacked.json" "$R/work/snap_$ARM"
for_each flatten bash "$HERE/run_flatten.sh" "$ARM"
FINALS=()
for w in "${LIVE[@]}"; do FINALS+=("$R/work/final_$ARM/$w.tifxyz"); done
stage orient "$PYW" -I "$HERE/studio_band.py" orient "$OUT/orient.json" "${FINALS[@]}" --umbilicus "$R/dataset/umbilicus.json"
for_each render render_one
for_each studio studio
stage summarise "$PYW" -I "$HERE/studio_band.py" summarise "$OUT/summary" "$OUT/maps" "$R/work/render_$ARM"
echo "READ_EXIT $ARM ${#LIVE[@]} windings read $(date -Is)"
