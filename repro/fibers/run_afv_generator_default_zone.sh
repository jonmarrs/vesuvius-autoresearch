#!/bin/bash
# Finding 107's run (docs/preregistration/2026-11-08_afv_generator_default_zone.md): fetch the 1088³ scan around the
# cube, run the 1024³ zone in 8 blocks of 512 with villa main's stitching and with the amended patch, then write the
# record once. Resumable: the fetch caches each slice's window, and each block's field is cached in WORK.
#
#   WORK=DIR VILLA=CLONE PATCHED=STITCH_PY [DEVICE=cpu] bash repro/fibers/run_afv_generator_default_zone.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${WORK:?a work directory}"
VILLA="${VILLA:?a villa clone holding 7e6b82164}"
PATCHED="${PATCHED:?the amended patch's extend/stitch.py}"
DEVICE="${DEVICE:-cpu}"
PY=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/venv/bin/python
PR=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/pr1934/vesuvius/src
MAIN=7e6b82164d014ed485aa027011f31070923fc0a9
SCRIPT="$REPO/scripts/afv_generator_default_zone.py"
mkdir -p "$WORK"
echo "ZONE_START $(git -C "$REPO" rev-parse HEAD) device $DEVICE $(date -Is)"
if [ ! -f "$WORK/context.npy" ]; then
  nice -n 19 "$PY" -I "$SCRIPT" fetch --out "$WORK/context.npy" --cache "$WORK/cache"
fi
echo "RUN $(date -Is)"
HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=$([ "$DEVICE" = cpu ] && echo "" || echo "${CUDA_VISIBLE_DEVICES:-0}") nice -n 19 \
  "$PY" -I "$SCRIPT" run --context "$WORK/context.npy" --work "$WORK" --pr "$PR" --villa "$VILLA" --main "$MAIN" \
  --patched-stitch "$PATCHED" --device "$DEVICE"
"$PY" -I "$SCRIPT" verdict --work "$WORK" --out "$REPO/reports/afv_generator_default_zone.json"
echo "ZONE_DONE $(date -Is)"
