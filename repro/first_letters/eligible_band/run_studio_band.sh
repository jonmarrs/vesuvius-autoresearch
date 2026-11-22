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
# FL_OVERLAP=1 renders the windings in the background, in the same order, while Studio reads each winding as soon as
# its render is recorded. The commands, their inputs, gates and logs are the serial read's; only when each runs
# changes. The renders use the CPUs and Studio the GPU, which the serial read leaves idle in turn (PHerc. 0826,
# finding 125: 2.66 h of renders, then 4.41 h of Studio). Default 0, the serial read, as findings 125, 126 and 129
# ran or were registered.
# STUDIO_SKIP_EMPTY=1 runs Studio through pherc0211_control/studio_fast.py --skip-empty (finding 132): the winner's
# loop, file, weights, command and batch size, without the windows whose crop holds no CT. Default 0, the winner's
# inference.py, as every read before finding 133.
#
# usage: FL_SCROLL=PHerc0826 [STUDIO_WINDINGS=FILE] [STUDIO_TILING=winner|published] [FL_OVERLAP=0|1]
#        [STUDIO_SKIP_EMPTY=0|1] run_studio_band.sh ARM
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
case "${FL_OVERLAP:-0}" in
  0|1) ;;
  *) echo "FL_OVERLAP is 0 or 1, not '$FL_OVERLAP'" >&2; exit 2 ;;
esac
case "${STUDIO_SKIP_EMPTY:-0}" in
  0) RUNNER=(inference.py) ;;
  1) RUNNER=(-I "$ROOT/repro/first_letters/pherc0211_control/studio_fast.py" run --code "$CODE" --skip-empty) ;;
  *) echo "STUDIO_SKIP_EMPTY is 0 or 1, not '$STUDIO_SKIP_EMPTY'" >&2; exit 2 ;;
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
  (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" "${RUNNER[@]}" \
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

render_and_read() {  # FL_OVERLAP=1: the render and Studio loops at once, each winding read once it is rendered
  local done_file=$OUT/rendered.txt renderer w t0 rc read_ok=()
  : > "$done_file"
  (
    for w in "${LIVE[@]}"; do
      t0=$(date +%s)
      render_one "$w" > "$R/logs/studio_${ARM}_render_$w.log" 2>&1
      rc=$?
      gate "$ARM" "studio_render_$w" "$rc" "$(( $(date +%s) - t0 ))"
      [ "$rc" -eq 0 ] || echo "FAILED render $w"
      echo "$w $rc" >> "$done_file"
    done
    echo "render: $(awk '$2 == 0' "$done_file" | wc -l) windings go on $(date -Is)"
  ) &
  renderer=$!
  for w in "${LIVE[@]}"; do
    while :; do
      rc=$(awk -v n="$w" '$1 == n {print $2}' "$done_file")
      [ -n "$rc" ] && break
      if ! kill -0 "$renderer" 2>/dev/null; then  # the renderer is gone: a last look, then no render
        rc=$(awk -v n="$w" '$1 == n {print $2}' "$done_file")
        [ -n "$rc" ] || { rc=gone; echo "FAILED render $w (the renderer stopped first)"; }
        break
      fi
      sleep "${FL_OVERLAP_POLL:-2}"
    done
    [ "$rc" = 0 ] || continue
    t0=$(date +%s)
    studio "$w" > "$R/logs/studio_${ARM}_studio_$w.log" 2>&1
    rc=$?
    gate "$ARM" "studio_studio_$w" "$rc" "$(( $(date +%s) - t0 ))"
    if [ "$rc" -eq 0 ]; then read_ok+=("$w"); else echo "FAILED studio $w"; fi
  done
  wait "$renderer"
  LIVE=("${read_ok[@]}")
  echo "studio: ${#LIVE[@]} windings go on $(date -Is)"
}

if [ -n "${STUDIO_WINDINGS:-}" ]; then
  ls "$MESHES" | grep -E '^w[0-9]+$' | grep -Fxf "$STUDIO_WINDINGS" > "$R/work/windings_$ARM.txt"
else
  ls "$MESHES" | grep -E '^w[0-9]+$' > "$R/work/windings_$ARM.txt"
fi
[ -s "$R/work/windings_$ARM.txt" ] || { echo "no windings to read" >&2; exit 2; }
mapfile -t LIVE < "$R/work/windings_$ARM.txt"
echo "READ_START $ARM ${#LIVE[@]} windings tiling=${STUDIO_TILING:-winner} skip_empty=${STUDIO_SKIP_EMPTY:-0} overlap=${FL_OVERLAP:-0} $(date -Is)"
stage snap bash "$HERE/run_snap.sh" "$ARM"
stage stacked "$PYW" -I "$HERE/studio_band.py" stacked "$OUT/stacked.json" "$R/work/snap_$ARM"
for_each flatten bash "$HERE/run_flatten.sh" "$ARM"
FINALS=()
for w in "${LIVE[@]}"; do FINALS+=("$R/work/final_$ARM/$w.tifxyz"); done
stage orient "$PYW" -I "$HERE/studio_band.py" orient "$OUT/orient.json" "${FINALS[@]}" --umbilicus "$R/dataset/umbilicus.json"
if [ "${FL_OVERLAP:-0}" = 1 ]; then
  render_and_read
else
  for_each render render_one
  for_each studio studio
fi
stage summarise "$PYW" -I "$HERE/studio_band.py" summarise "$OUT/summary" "$OUT/maps" "$R/work/render_$ARM"
echo "READ_EXIT $ARM ${#LIVE[@]} windings read $(date -Is)"
