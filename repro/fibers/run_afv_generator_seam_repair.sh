#!/bin/bash
# Finding 140's run (docs/preregistration/2026-11-27_afv_generator_seam_repair.md): the review-repaired seam trim of
# villa #2711 on findings 106's and 109's cached per-block fiber fields, beside villa main and finding 106's trim; then
# the record, written once; then addendum 1, finding 107's 1024³ zone. Each cube runs once; a finished cube is skipped.
#
#   OUT=DIR OLD_FIRST=STITCH_PY OLD_ZONE=STITCH_PY REPAIRED=STITCH_PY bash repro/fibers/run_afv_generator_seam_repair.sh
#
# OLD_FIRST and OLD_ZONE: villa 7e6b82164 with repro/fibers/villa_fiber_generator_trim_cut_ends{,_zone}_7e6b82164.patch
# (sha256 c9ab1700…, 362b78b1…); REPAIRED: villa 9c1afbb1b with
# repro/fibers/villa_fiber_generator_trim_cut_ends_repaired_9c1afbb1b.patch (extend/stitch.py, sha256 62eddc21…).
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:?an output directory}"
OLD_FIRST="${OLD_FIRST:?finding 106's first-form stitch.py}"
OLD_ZONE="${OLD_ZONE:?finding 107's zone-form stitch.py}"
REPAIRED="${REPAIRED:?the repaired stitch.py}"
GEN=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen
PY=$GEN/venv/bin/python
PR=$GEN/pr1934/vesuvius/src
SCRIPT="$REPO/scripts/afv_generator_seam_repair.py"
echo "SR_START $(git -C "$REPO" rev-parse HEAD) $(date -Is)"
SPECS=$("$PY" -I -c "import sys; sys.path.insert(0, '$REPO/scripts'); import afv_generator_seam_repair as r; print(*[s + ':' + c for s, (cs, _k) in r.SETS.items() for c in cs])")
for spec in $SPECS; do
  set_=${spec%%:*}; cube=${spec##*:}
  [ -f "$OUT/$set_/$cube/result.json" ] && { echo "SKIP $spec"; continue; }
  fields=$GEN/$([ "$set_" = scroll3 ] && echo block_seams || echo seam_confirmation)
  echo "RUN $spec $(date -Is)"
  HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES="" nice -n 10 "$PY" -I "$SCRIPT" run "$set_" "$cube" --fields "$fields" \
    --out "$OUT" --pr "$PR" --old-first "$OLD_FIRST" --old-zone "$OLD_ZONE" --repaired "$REPAIRED" || echo "FAILED $spec"
done
"$PY" -I "$SCRIPT" verdict --out "$OUT" --record "$REPO/reports/afv_generator_seam_repair.json"
HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES="" nice -n 10 "$PY" -I "$SCRIPT" zone --work "$GEN/default_zone" --out "$OUT" \
  --pr "$PR" --old-zone "$OLD_ZONE" --repaired "$REPAIRED"
echo "SR_DONE $(date -Is)"
