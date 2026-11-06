#!/usr/bin/env bash
# The registered held-out run of docs/preregistration/2026-11-06_afv_generator_block_seams.md: the eight Scroll-3 512³
# cubes, one at a time at nice 19, then the verdict, written once.
#
#   WORK=<dir> VILLA=<villa clone with 7e6b82164 and the patch applied in a worktree> PATCHED=<its stitch.py> \
#     [DEVICE=cpu] repro/fibers/run_afv_generator_block_seams_chain.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${WORK:?a work directory}"
VILLA="${VILLA:?a villa clone holding 7e6b82164}"
PATCHED="${PATCHED:?the patched extend/stitch.py}"
DEVICE="${DEVICE:-cpu}"
PY=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/venv/bin/python
PR=/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/pr1934/vesuvius/src
MAIN=7e6b82164d014ed485aa027011f31070923fc0a9
mkdir -p "$WORK"
echo "CHAIN_START $(git -C "$REPO" rev-parse HEAD) device $DEVICE $(date -Is)"
for c in $("$PY" -I -c "import sys; sys.path.insert(0, '$REPO/scripts'); import afv_generator_block_seams as b; print(*b.HELD_OUT)"); do
  if [ -f "$WORK/$c/result.json" ]; then echo "SKIP $c (done)"; continue; fi
  echo "RUN $c $(date -Is)"
  HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=$([ "$DEVICE" = cpu ] && echo "" || echo "${CUDA_VISIBLE_DEVICES:-0}") nice -n 19 \
    "$PY" -I "$REPO/scripts/afv_generator_block_seams.py" run "$c" --work "$WORK" --pr "$PR" --villa "$VILLA" \
    --main "$MAIN" --patched-stitch "$PATCHED" --device "$DEVICE" || echo "FAILED $c"
done
"$PY" -I "$REPO/scripts/afv_generator_block_seams.py" verdict --work "$WORK" --out "$REPO/reports/afv_generator_block_seams.json"
echo "CHAIN_DONE $(date -Is)"
