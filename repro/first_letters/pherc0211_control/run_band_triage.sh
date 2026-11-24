#!/usr/bin/env bash
# Finding 138: a Studio band read of PHerc. 211's band z 7650-9150 (finding 119's fit), and the PHerc. 306B team's
# window triage of it. Does the triage put the winner's text first?
# Registration: docs/preregistration/2026-11-22_first_letters_0211_band_triage.md. Runs once, under
# run_after_controls.sh (finding 133's choices: STUDIO_SKIP_EMPTY=1, FL_DENSIFY=2, FL_SNAP_PASSES=3), each step only
# if the one before exited 0:
#   check    finding 119's fit and its quality record are on disk, nothing of this read is, the controls' choices
#            are finding 133's, and the glyph weights match glyph.py's sha256 (fetched if missing)
#   select   studio_band.py select: the raw windings with positive excess, before any ink (finding 126's rule)
#   densify  those windings subdivided twice (finding 130), as arm fulldense
#   read     run_studio_band.sh fulldense with FL_OVERLAP=1, as finding 133 reads PHerc. 0800
#   glyph    triage/glyph.py score: every window of every read winding
#   place    band_triage.py place: the windows that hold the winner's place
#   verdict  band_triage.py verdict
# Studio's and the glyph CNN's weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_after_controls.sh bash run_band_triage.sh
set -u
export FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150
HERE=$(cd "$(dirname "$0")" && pwd)
BAND=$(cd "$HERE/../eligible_band" && pwd)
TRIAGE=$(cd "$HERE/../triage" && pwd)
. "$HERE/env.sh"  # the band's R, fit_meshes, gate and finding 118's C, WINNER, SEG, RENDER, MAPS
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
ARM=fulldense
OUT=$C/work/band_triage
GLYPH_DIR=$FL_ROOT/triage_inputs
[ -e "$OUT" ] && { echo "$OUT exists: finding 138 runs once" >&2; exit 2; }
for d in fit_$ARM snap_$ARM final_$ARM render_$ARM studio_$ARM; do
  [ -e "$R/work/$d" ] && { echo "$R/work/$d exists" >&2; exit 2; }
done
mkdir -p "$OUT/logs" "$OUT/gate"

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
  [ -f "$R/work/quality_full.json" ] || { echo "finding 119's quality record is missing" >&2; return 1; }
  fit_meshes full > /dev/null || return 1
  [ "${STUDIO_SKIP_EMPTY:-}" = 1 ] && [ "${FL_DENSIFY:-}" = 2 ] && [ "${FL_SNAP_PASSES:-}" = 3 ] \
    || { echo "not finding 133's choices: run under run_after_controls.sh" >&2; return 1; }
  bash "$TRIAGE/fetch_glyph.sh" "$GLYPH_DIR"
}
densify() {  # run_band_and_read.sh's densify_selected
  local base dest w
  base=$(fit_meshes full) || return 1
  dest=$R/work/fit_$ARM/densified/meshes/fitted
  mkdir -p "$dest"
  while read -r w; do
    "$PYW" -I "$BAND/densify_winding.py" "$base/$w" "$dest/$w" --factor "$FL_DENSIFY" || return 1
  done < "$OUT/selected.txt"
}

step check check
step select "$PYW" -I "$BAND/studio_band.py" select "$R/work/quality_full.json" "$OUT/selected.txt"
step densify densify
step read env FL_OVERLAP=1 STUDIO_WINDINGS="$OUT/selected.txt" bash "$BAND/run_studio_band.sh" "$ARM"
step glyph "$PYW" -I "$TRIAGE/glyph.py" score "$OUT/glyph.json" "$R/work/studio_$ARM/maps" "$R/work/render_$ARM" \
  "$R/work/windings_$ARM.txt" --weights "$GLYPH_DIR/gA.pt" --um "$VOXEL_UM"
step place "$PYW" -I "$HERE/band_triage.py" place "$OUT/place.json" --winner-mesh "$SEG" --winner-maps "$MAPS" \
  --winner-render "$RENDER" --studio-mask "$WINNER/v9/studiosoft-mask.png" --finals "$R/work/final_$ARM" \
  --renders "$R/work/render_$ARM" --list "$R/work/windings_$ARM.txt"
step verdict "$PYW" -I "$HERE/band_triage.py" verdict "$OUT/triage.json" "$OUT/glyph.json" "$OUT/place.json"
cat "$OUT/logs/verdict.log"
