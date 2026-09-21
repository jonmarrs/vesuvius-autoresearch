#!/usr/bin/env bash
# Render ink from a spiral fit using published artifacts only. THIS IS THE PATH
# THAT WORKS; see README for the four obstacles and the one dead end.
#
# Key choice: villa's run_single.py passes NO --strips, so the default full-scroll
# + LASAGNA flatten is the real pipeline. The --strips/flatboi path is a side road
# and does not converge here (9h12m on a clean manifold 12.5k-vertex mesh).
#
# Split execution, because there is no nvidia container runtime on this box:
#   python (render_ink.py + lasagna flatten) runs on the HOST, using the GPU;
#   the native vc_* binaries run in the container via bin/ wrappers, which mount
#   the workspace at an IDENTICAL path so absolute arguments need no translation.
set -euo pipefail

W="${1:?usage: run_render.sh <workdir with meshes/ spiral-fitting/ lasagna/ vesuvius/ bin/>}"
VENV="${VENV:-/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python}"
INK_URL="${INK_URL:-https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr}"

cd "$W/spiral-fitting"
# lasagna/fit.py imports vc3d_fiber_format, which lives in villa's vesuvius/src,
# NOT in lasagna/. Without this the flatten dies on import.
#
# FLATTEN_DETERMINISTIC=1 makes the lasagna flatten BIT-REPRODUCIBLE. Its
# run-to-run variation is CUDA reduction order and nothing else (no RNG on the
# path): two stock flattens of one mesh set land 7.15 vx apart and move
# total_fg_pixels 3.04%; under deterministic algorithms they are byte-identical.
# Cost ~9.5x on the flatten, ~11 min instead of ~4, against 2h renders. The shim
# is a sitecustomize.py that activates only when the variable is set, so
# leaving it on PYTHONPATH unconditionally changes nothing for stock runs.
# reports/the_flatten_is_reproducible_when_asked.md
HERE_RR="$(cd "$(dirname "$0")" && pwd)"
if [ "${FLATTEN_DETERMINISTIC:-}" = "1" ]; then
  echo "[run_render] FLATTEN_DETERMINISTIC=1: flatten will be bit-reproducible (~9.5x slower)" >&2
fi
PYTHONPATH="$HERE_RR/determinism_shim:$W/vesuvius/src" exec "$VENV" -u render_ink.py "$W/meshes" \
  --volume "$W/inkcache" --remote-url "$INK_URL" \
  --vc-render-bin "$W/bin/vc_render_tifxyz" \
  --tifxyz-trim-bin "$W/bin/vc_tifxyz_trim" \
  --lasagna-dir "$W/lasagna" --lasagna-device cuda \
  --num-processes 1
