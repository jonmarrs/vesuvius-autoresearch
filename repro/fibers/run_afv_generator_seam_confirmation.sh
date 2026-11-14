#!/bin/bash
# Finding 109's run (docs/preregistration/2026-11-09_afv_generator_seam_confirmation.md): predict and generate the ten
# fiber-skeletons cubes ScrollGT does not ship, as one block and in 8 blocks, stitched as villa main, with the seam
# trim, and with the trim and the cross-block duplicate change; then write the record once. Resumable per cube.
#
#   WORK=DIR VILLA=CLONE PATCHED=STITCH_PY CATALOG=CATALOG_PY bash repro/fibers/run_afv_generator_seam_confirmation.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${WORK:?a work directory}"
VILLA="${VILLA:?a villa clone holding 7e6b82164}"
PATCHED="${PATCHED:?the amended seam-trim stitch.py}"
CATALOG="${CATALOG:?the catalog.py with the cross-block duplicate change}"
PY=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/venv/bin/python
PR=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/pr1934/vesuvius/src
MAIN=7e6b82164d014ed485aa027011f31070923fc0a9
SCRIPT="$REPO/scripts/afv_generator_seam_confirmation.py"
mkdir -p "$WORK"
echo "SC_START $(git -C "$REPO" rev-parse HEAD) $(date -Is)"
# The 256³ cubes first, then the 512³ ones.
CUBES=$("$PY" -I -c "import sys; sys.path.insert(0, '$REPO/scripts'); import afv_generator_seam_confirmation as sc; print(' '.join(sorted(sc.CUBES, key=sc.size_of)))")
for CUBE in $CUBES; do
  if [ ! -f "$WORK/$CUBE/result.json" ]; then
    CUDA_VISIBLE_DEVICES= nice -n 19 "$PY" -I "$SCRIPT" run --cube "$CUBE" --work "$WORK" --pr "$PR" --villa "$VILLA" \
      --main "$MAIN" --patched-stitch "$PATCHED" --patched-catalog "$CATALOG"
  fi
done
"$PY" -I "$SCRIPT" verdict --work "$WORK" --out "$REPO/reports/afv_generator_seam_confirmation.json"
echo "SC_DONE $(date -Is)"
