#!/usr/bin/env bash
# Finding 126: fit a band of an eligible scroll with the recipe, unchanged, and read it with Studio, as finding 125
# read PHerc. 0826. Registration: docs/preregistration/2026-11-20_first_letters_0358_band_read.md. Each step only if
# the one before exited 0:
#   fetch_volumes, fetch_tracks, make_dataset   the band's public inputs (anonymous reads) and villa's dataset
#   sdt                                         the distance field of the surface prediction
#   fit_smoke, fit_full                         300 steps, then the registered 30,000-step fit at villa's defaults
#   quality                                     the sheet-following excess of every raw winding
#   select                                      the windings with positive excess, before any ink
#   densify                                     with FL_DENSIFY=F only: those raw windings subdivided F times
#                                               (densify_winding.py, finding 130) into arm fulldense
#   read                                        run_studio_band.sh on those windings: arm full, or fulldense
# Each step's exit and seconds go to R/work/gate_chain/<step>.json, beside the scripts' own records.
#
# usage: FL_SCROLL=PHerc0358 FL_Z_BEGIN=8872 FL_Z_END=10372 [FL_DENSIFY=2] run_band_and_read.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
[ -e "$R/work/fit_full" ] && { echo "$R/work/fit_full exists: the band is fitted once" >&2; exit 2; }
mkdir -p "$R/logs"

step() {  # NAME COMMAND...: run, record the gate, stop the chain on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$R/logs/chain_$name.log" 2>&1
  rc=$?
  gate chain "$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

step fetch_volumes bash "$HERE/setup/fetch_volumes.sh"
step fetch_tracks bash "$HERE/setup/fetch_tracks.sh"
step make_dataset bash "$HERE/setup/make_dataset.sh"
step sdt bash "$HERE/run_sdt.sh"
step fit_smoke bash "$HERE/run_fit.sh" smoke 300
step fit_full bash "$HERE/run_fit.sh" full
step quality bash "$HERE/run_quality.sh" full
step select "$PYW" -I "$HERE/studio_band.py" select "$R/work/quality_full.json" "$R/work/studio_windings_full.txt"
densify_selected() {  # the selected raw windings of arm full, subdivided FL_DENSIFY times, as arm fulldense
  local base dest w
  base=$(fit_meshes full) || return 1
  dest=$R/work/fit_fulldense/densified/meshes/fitted
  [ -e "$R/work/fit_fulldense" ] && { echo "$R/work/fit_fulldense exists" >&2; return 1; }
  mkdir -p "$dest"
  while read -r w; do
    "$PYW" -I "$HERE/densify_winding.py" "$base/$w" "$dest/$w" --factor "$FL_DENSIFY" || return 1
  done < "$R/work/studio_windings_full.txt"
}

READ_ARM=full
if [ -n "${FL_DENSIFY:-}" ]; then
  READ_ARM=fulldense
  step densify densify_selected
fi
step read env STUDIO_WINDINGS="$R/work/studio_windings_full.txt" bash "$HERE/run_studio_band.sh" "$READ_ARM"
cat "$R/logs/chain_read.log" | tail -5
