#!/bin/bash
# Finding 108's run (docs/preregistration/2026-11-09_afv_generator_cross_block_duplicates.md): stitch finding 106's eight
# held-out cubes and finding 107's zone from their cached fields, with the seam trim and with the trim and the
# cross-block duplicate change, then write the record once. No field is predicted. Resumable per cube.
#
#   WORK=DIR VILLA=CLONE PATCHED=STITCH_PY CATALOG=CATALOG_PY bash repro/fibers/run_afv_generator_cross_block_duplicates.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${WORK:?a work directory}"
VILLA="${VILLA:?a villa clone holding 7e6b82164}"
PATCHED="${PATCHED:?the amended seam-trim stitch.py}"
CATALOG="${CATALOG:?the catalog.py with the cross-block duplicate change}"
PY=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/venv/bin/python
PR=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/pr1934/vesuvius/src
FIELDS=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/block_seams
ZONE=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/default_zone
MAIN=7e6b82164d014ed485aa027011f31070923fc0a9
SCRIPT="$REPO/scripts/afv_generator_cross_block_duplicates.py"
COMMON=(--work "$WORK" --pr "$PR" --villa "$VILLA" --main "$MAIN" --patched-stitch "$PATCHED" --patched-catalog "$CATALOG")
mkdir -p "$WORK"
echo "XD_START $(git -C "$REPO" rev-parse HEAD) $(date -Is)"
for CUBE in $("$PY" -I -c "import sys; sys.path.insert(0, '$REPO/scripts'); import afv_generator_block_seams as bs; print(' '.join(bs.HELD_OUT))"); do
  if [ ! -f "$WORK/$CUBE.json" ]; then
    CUDA_VISIBLE_DEVICES= nice -n 19 "$PY" -I "$SCRIPT" run --cube "$CUBE" --fields "$FIELDS" "${COMMON[@]}"
  fi
done
if [ ! -f "$WORK/zone.json" ]; then
  CUDA_VISIBLE_DEVICES= nice -n 19 "$PY" -I "$SCRIPT" zone --zone-work "$ZONE" "${COMMON[@]}"
fi
"$PY" -I "$SCRIPT" verdict --work "$WORK" --out "$REPO/reports/afv_generator_cross_block_duplicates.json"
echo "XD_DONE $(date -Is)"
