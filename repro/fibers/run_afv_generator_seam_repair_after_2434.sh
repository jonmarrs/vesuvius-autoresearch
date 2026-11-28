#!/bin/bash
# Finding 140, addendum 2 (docs/preregistration/2026-11-27_afv_generator_seam_repair.md): main and the repaired trim
# of villa #2711, both with villa #2434, on findings 106's and 109's cached per-block fiber fields and finding 107's
# 1024³ zone. First the gate cube runs again exactly as finding 140 ran it; then each cube once; then the record,
# written once. A finished cube is skipped.
#
#   OUT=DIR PIN=DIR bash repro/fibers/run_afv_generator_seam_repair_after_2434.sh
#
# PIN holds finding 140's three files (stitch_first_7e6b82164.py c9ab1700…, stitch_zone_7e6b82164.py 362b78b1…,
# stitch_accc6d59c.py 62eddc21…) and #2711's head extend/stitch.py (stitch_8a7f76803.py, 60d4bc10…). PKG is #1934's
# package with repro/fibers/villa_2434_on_pr1934_afv_spline_generator.patch applied (patch -p1 in its vesuvius/).
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:?an output directory}"
PIN="${PIN:?the directory of pinned stitch.py files}"
GEN=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen
PY=$GEN/venv/bin/python
PR=$GEN/pr1934/vesuvius/src
PKG="${PKG:-$GEN/pr1934_2434/vesuvius/src}"
SCRIPT="$REPO/scripts/afv_generator_seam_repair.py"
F140="$REPO/reports/afv_generator_seam_repair.json"
RUN=(env HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES="" nice -n 10 "$PY" -I "$SCRIPT")
GATED=(--out "$OUT" --pr "$PKG" --pr1934 "$PR" --repaired "$PIN/stitch_8a7f76803.py" --gate "$OUT/gate" --f140 "$F140")
echo "A2_START $(git -C "$REPO" rev-parse HEAD) $(date -Is)"
GATE_CUBE=$("$PY" -I -c "import sys; sys.path.insert(0, '$REPO/scripts'); import afv_generator_seam_repair as r; print(r.GATE_CUBE)")
if [ ! -f "$OUT/gate/scroll3/$GATE_CUBE/result.json" ]; then
  echo "GATE $GATE_CUBE $(date -Is)"
  "${RUN[@]}" run scroll3 "$GATE_CUBE" --fields "$GEN/block_seams" --out "$OUT/gate" --pr "$PR" \
    --old-first "$PIN/stitch_first_7e6b82164.py" --old-zone "$PIN/stitch_zone_7e6b82164.py" \
    --repaired "$PIN/stitch_accc6d59c.py" || { echo "GATE_FAILED"; exit 1; }
fi
SPECS=$("$PY" -I -c "import sys; sys.path.insert(0, '$REPO/scripts'); import afv_generator_seam_repair as r; print(*[s + ':' + c for s, (cs, _k) in r.SETS.items() for c in cs])")
for spec in $SPECS; do
  set_=${spec%%:*}; cube=${spec##*:}
  [ -f "$OUT/$set_/$cube/result.json" ] && { echo "SKIP $spec"; continue; }
  fields=$GEN/$([ "$set_" = scroll3 ] && echo block_seams || echo seam_confirmation)
  echo "RUN $spec $(date -Is)"
  "${RUN[@]}" after2434 "$set_" "$cube" --fields "$fields" "${GATED[@]}" || echo "FAILED $spec"
done
[ -f "$OUT/zone/result.json" ] || "${RUN[@]}" zone2434 --work "$GEN/default_zone" "${GATED[@]}" || echo "FAILED zone"
"$PY" -I "$SCRIPT" record2434 --out "$OUT" --gate "$OUT/gate" --f140 "$F140" \
  --record "$REPO/reports/afv_generator_seam_repair_after_2434.json"
echo "A2_DONE $(date -Is)"
