#!/usr/bin/env bash
# Finding 138's consequence for one eligible band read: score every window of its Studio maps with the PHerc. 306B
# team's glyph network (glyph.py score, as finding 138 ran it), then write the band page's look-first list
# (look_first.py). Both stay in the band's run directory; nothing is uploaded. Approved by the owner on 2026-11-23.
#
# usage: FL_SCROLL=PHercNNNN run_look_first.sh ARM
#   ARM  the read arm whose maps and renders are scored (fulldense, or outer80 for PHerc. 0826)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: FL_SCROLL=PHercNNNN run_look_first.sh ARM}
FL_SENSE=${FL_SENSE:-CW}  # env.sh asks for it only for PHerc. 0125; the scoring does not use it
export FL_SENSE
. "$HERE/../eligible_band/env.sh"
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
OUT=$R/work/studio_$ARM
[ -d "$OUT/summary/images_reading" ] || { echo "$OUT/summary has no reading images: run band_index.py first" >&2; exit 2; }
"$PYW" -I "$HERE/glyph.py" score "$OUT/glyph.json" "$OUT/maps" "$R/work/render_$ARM" "$R/work/windings_$ARM.txt" \
  --weights "$FL_ROOT/triage_inputs/gA.pt" --um "$VOXEL_UM"
"$PYW" -I "$HERE/look_first.py" "$OUT/summary" "$OUT/glyph.json"
