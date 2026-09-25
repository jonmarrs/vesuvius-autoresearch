#!/usr/bin/env bash
# docs/preregistration/2026-09-24_upstream_fitter.md -- three arms, serial.
# Per seed: fit on villa 75c79ac5f -> work dir on the PINNED render path (be09a8503,
# same image, deterministic flatten) over the scored windings w120-w129 -> render ->
# score. Exactly the path detfit_s4..s9 took; only the fitter differs.
# Launch: setsid nohup ./run_upstream_fitter_chain.sh >> <log> 2>&1 & disown
set -uo pipefail
OUT=/home/jon/openclaw-workspace/Neo-VM/spiral_out
LOG=${CHAIN_LOG:-$OUT/upstream_fitter_chain.log}
HERE="$(cd "$(dirname "$0")" && pwd)"
FITS="$HERE/../spiral_fits"
UPTREE=/home/jon/openclaw-workspace/Neo-VM/villa-spiral-upstream
export RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
export FLATTEN_DETERMINISTIC=1
export INK_METRIC_SERIAL_FOLDS=1
export VILLA_REF=be09a85035059fd83471b1632b5898c62f2c65b1
export VILLA_REF_EXPLICIT=1
# Explicit: setup_workdir.sh's default (../../villa beside itself) is an EMPTY
# submodule dir in a worktree and absent in an installed copy.
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
git -C "$VILLA" cat-file -e "$VILLA_REF^{commit}" || { echo "VILLA_REF_MISSING in $VILLA"; exit 2; }
cd "$HERE"
for S in 1 2 3; do
  TAG=upfit_s$S
  W=$OUT/detfit_up$S
  echo "=========== ARM $TAG starting $(date -Is) ==========="
  if [ -e "$W" ]; then echo "WORKDIR_EXISTS $W -- refusing to overwrite"; exit 3; fi
  bash "$FITS/fit_upfit.sh" "$S" || { echo "FIT_FAILED $TAG"; exit 1; }
  FITTED=$(ls -d "$OUT"/*-patch_"$TAG"/meshes/fitted_"$TAG" 2>/dev/null | tail -1)
  [ -n "$FITTED" ] || { echo "FIT_OUTPUT_MISSING $TAG"; exit 1; }
  N=$(ls -d "$FITTED"/w*_spliced_"$TAG" | wc -l)
  [ "$N" -eq 120 ] || { echo "FIT_WINDINGS_WRONG $TAG: $N spliced (want 120)"; exit 1; }
  echo "FIT_DONE $TAG $(date -Is)"
  ./setup_workdir.sh "$W" "$FITTED" 120 121 122 123 124 125 126 127 128 129 \
    || { echo "SETUP_FAILED $TAG"; exit 1; }
  cp "$UPTREE/VILLA_SHA" "$W/FIT_TREE"
  VENV="$RENDER_VENV" ./run_render.sh "$W" &
  RP=$!
  for i in $(seq 1 36); do
    sleep 5
    grep -q "determinism-shim\] torch.use_deterministic" <(tail -c 200000 "$LOG") && break
    if [ "$i" -eq 36 ]; then echo "GUARD_FAILED $TAG: shim never activated"; kill $RP; exit 2; fi
  done
  echo "GUARD_OK $TAG"
  wait $RP || { echo "RENDER_FAILED $TAG"; exit 1; }
  ./score_arms.sh "$W" || { echo "SCORE_FAILED $TAG"; exit 1; }
  echo "ARM_DONE $TAG $(date -Is)"
done
echo "UPSTREAM_CHAIN_DONE $(date -Is)"
