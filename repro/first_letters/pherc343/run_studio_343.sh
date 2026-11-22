#!/usr/bin/env bash
# Finding 127: Studio at the place where the PHerc. 343 recipe's published image shows 18 letters.
# Registration: docs/preregistration/2026-11-20_first_letters_343_studio.md. Each step only if the one before
# exited 0:
#   check      finding 123's weights and the winner's inference.py against their SHA-256 values
#   reference  the recipe's make_submission_image.py, the published command plus --write-components: u, the
#              8-bit ensemble ink image; its PNG must be finding 110's rebuild
#   planes     studio_e2e.py planes: finding 110's render, layers 41 down to 26, and reversed (the other side)
#   infer      the winner's inference.py with the winner's command, in finding 123's environment, on both
#   compare    studio_343.py compare
# The weights and outputs (CC BY-NC 4.0) stay on this machine.
#
# usage: run_studio_343.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
FL_ROOT=${FL_ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters}
B=$FL_ROOT/pherc343_repro
C=$FL_ROOT/pherc0211_control
N=concat_w047-w048_R5B2_z9500-11000
REPO=$B/src/repo
W=$B/work
M=$W/maps
RENDER=$W/${N}_66.zarr
PY343="$B/venv/bin/python -I"
PYW=${PYW:-$ROOT/.venv/bin/python}
ENV=$C/work/studio_env
WEIGHTS=$C/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$C/inputs/winner/v9/inference
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
PNG_SHA=8954ae313a0eea3dad91621152aa00a90c4b9d0c547ea6ce80134d1300f6509a  # finding 110's rebuild
OUT=$W/studio_343
[ -e "$OUT" ] && { echo "$OUT exists: finding 127 runs once" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's environment is missing" >&2; exit 2; }
[ -d "$RENDER/0" ] || { echo "finding 110's render is missing" >&2; exit 2; }
mkdir -p "$OUT/planes" "$OUT/maps" "$OUT/reference" "$OUT/logs" "$OUT/gate"

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

reference() {
  (cd "$W/mesh" && sha256sum $N.tifxyz/x.tif $N.tifxyz/y.tif $N.tifxyz/z.tif $N.tifxyz/meta.json) > "$OUT/reference/mesh_sums" || return 1
  $PY343 "$REPO/ink/scripts/make_submission_image.py" --mesh "$W/mesh/$N.tifxyz" \
    --umbilicus "$REPO/inputs/umbilicus_PHerc0343.json" --ct "$RENDER" --overlay-style dimmed-ct --caption compact \
    --geometry-sums "$OUT/reference/mesh_sums" --area 380,105,6021,2560 --max-cm2 12 --ct-layer d+1 \
    --ink "$M/${N}__dnative__L66s26_reverse.tif" "$M/${N}__hecate__L66zc33.50_reverse.png" \
          "$M/${N}__hybrid_3d2d-seed42__L66s26_reverse.tif" "$M/${N}__hybrid_3d2d-seed43__L66s26_reverse.tif" \
    --ensemble --ink-stats "$W/images/${N}__stats.json" \
    --rows "$REPO/inputs/${N}_rows.json" --letters "$REPO/inputs/${N}_letter_boxes.json" --letter-markers off \
    --sizes-csv "$OUT/reference/${N}_letter_sizes.csv" --out-dir "$OUT/reference" --write-components || return 1
  echo "$PNG_SHA  $OUT/reference/$N.png" | sha256sum -c
}

planes() {
  "$PYW" -I "$ROOT/repro/first_letters/pherc0211_control/studio_e2e.py" planes "$RENDER" "$OUT/planes/forward.npy" || return 1
  "$PYW" -I "$ROOT/repro/first_letters/pherc0211_control/studio_e2e.py" planes "$RENDER" "$OUT/planes/reversed.npy" --reverse
}

infer() {
  local smi rc=0 peak name
  nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 2 > "$OUT/gpu.csv" &
  smi=$!
  for name in forward reversed; do
    echo "infer $name $(date -Is)"
    (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
       --input "$OUT/planes/$name.npy" --output "$OUT/maps/$name.npy" --checkpoint "$WEIGHTS" --stride 64 \
       --blend hann --batch-size 32) || { rc=1; break; }
  done
  kill "$smi" 2>/dev/null
  peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
  printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
  return $rc
}

step check bash -c "printf '%s  %s\n%s  %s\n' '$W_SHA' '$WEIGHTS' '$CODE_SHA' '$CODE/inference.py' | sha256sum -c"
step reference reference
step planes planes
step infer infer
step compare "$PYW" -I "$HERE/studio_343.py" compare "$OUT/studio_343.json" --render "$RENDER" \
  --sidecar "$OUT/reference/$N.json" --ink-png "$OUT/reference/${N}_ink.png" \
  --studio "$OUT/maps/forward.npy" --studio-reversed "$OUT/maps/reversed.npy" \
  --maps "$M" --image "$OUT/studio_343.png"
rm -f "$OUT/planes/forward.npy" "$OUT/planes/reversed.npy"
cat "$OUT/logs/compare.log"
