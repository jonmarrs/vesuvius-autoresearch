#!/usr/bin/env bash
# docs/preregistration/2026-09-25_upstream_render_path.md -- three render-only arms,
# serial, on the upfit_s1 meshes (w120-w129). Only VILLA_REF differs between arms.
# Launch: setsid nohup ./run_upstream_render_path_chain.sh >> <log> 2>&1 < /dev/null & disown
set -uo pipefail
OUT=/home/jon/openclaw-workspace/Neo-VM/spiral_out
LOG=${CHAIN_LOG:-$OUT/upstream_render_path_chain.log}
HERE="$(cd "$(dirname "$0")" && pwd)"
export RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
export FLATTEN_DETERMINISTIC=1
export INK_METRIC_SERIAL_FOLDS=1
export VILLA_REF_EXPLICIT=1
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
PIN=be09a85035059fd83471b1632b5898c62f2c65b1
UP=75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3
MESHES=$(ls -d "$OUT"/*-patch_upfit_s1/meshes/fitted_upfit_s1 | tail -1)
[ -n "$MESHES" ] || { echo "MESHES_MISSING"; exit 2; }
cd "$HERE"
for SPEC in "rpath_up_a:$UP" "rpath_up_b:$UP" "rpath_pin_a:$PIN"; do
  ARM=${SPEC%%:*}; REF=${SPEC#*:}
  W=$OUT/$ARM
  echo "=========== ARM $ARM ($REF) starting $(date -Is) ==========="
  if [ -e "$W" ]; then echo "WORKDIR_EXISTS $W -- refusing to overwrite"; exit 3; fi
  git -C "$VILLA" cat-file -e "$REF^{commit}" || { echo "VILLA_REF_MISSING $REF"; exit 2; }
  VILLA_REF=$REF ./setup_workdir.sh "$W" "$MESHES" 120 121 122 123 124 125 126 127 128 129 \
    || { echo "SETUP_FAILED $ARM"; exit 1; }
  [ "$(cat "$W/VILLA_SHA")" = "$REF" ] || { echo "SHA_WRONG $ARM"; exit 1; }
  # Count shim lines BEFORE this render and require a NEW one. The older chains grepped
  # the log tail, which back-to-back render-only arms would satisfy with the previous
  # arm's line.
  N0=$(grep -c "determinism-shim\] torch.use_deterministic" "$LOG" || true)
  VENV="$RENDER_VENV" ./run_render.sh "$W" &
  RP=$!
  for i in $(seq 1 36); do
    sleep 5
    N=$(grep -c "determinism-shim\] torch.use_deterministic" "$LOG" || true)
    [ "$N" -gt "$N0" ] && break
    if [ "$i" -eq 36 ]; then echo "GUARD_FAILED $ARM: shim never activated"; kill $RP; exit 2; fi
  done
  echo "GUARD_OK $ARM"
  wait $RP || { echo "RENDER_FAILED $ARM"; exit 1; }
  ./score_arms.sh "$W" || { echo "SCORE_FAILED $ARM"; exit 1; }
  echo "ARM_DONE $ARM $(date -Is)"
done
echo "RENDER_PATH_CHAIN_DONE $(date -Is)"
