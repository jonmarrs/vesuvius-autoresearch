#!/usr/bin/env bash
# docs/preregistration/2026-10-03_scorer_sensitivity_vs_labels.md -- the 8 labelled Scroll-1 segments, rendered at
# villa's metric settings (group 1, scale 0.25, 5 slices) in linear and smooth mode, strip-built like render_ink
# and scored by the pinned scorer with probabilities kept. Launch through run_snapshot.sh; helpers are frozen.
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
HERE="$(cd "$(dirname "$0")" && pwd)"
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
WORK=$SO/gt_interp/scorer_study
MESHES=$SO/gt_interp/study      # meshes fetched by the finding-71 chain, re-used
IMG=vc-render:sampler-f637f3b35
SHA=f637f3b35208bafa7812b4d97fea45bf43d19edb
VCHOME=$SO/interp_smoke/vchome
INK_URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr"
SEGS="20230702185753 20230929220926 20231007101619 20231012184424 20231016151002 20231031143852 20231106155351 20231210121321"
DISK_GUARD_GB=400
say() { echo "$*  $(date -Is)"; }

for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && { say "SC_ABORTED a render is running"; exit 3; }; done
[ -e "$WORK" ] && { say "SC_ABORTED $WORK exists"; exit 5; }
[ "$(docker run --rm --entrypoint cat $IMG /opt/vcsrc/SAMPLER_SHA)" = "$SHA" ] || { say "SC_ABORTED image sha"; exit 3; }
grep -q INK_METRIC_KEEP_PROB "$SO/gt_interp/scorer_tree/spiral-fitting/get_ink_metrics.py" || { say "SC_ABORTED scorer tree lacks keep-prob"; exit 3; }
[ -x "$HERE/score_arms.sh" ] && [ -f "$HERE/artifacts.py" ] || { say "SC_ABORTED helpers missing in $HERE"; exit 3; }
mkdir -p "$WORK" "$WORK/inkcache"
cp "$REPO/scripts/analyse_scorer_vs_labels.py" "$REPO/scripts/analyse_interp_vs_labels.py" "$WORK/" || { say "SC_ABORTED freeze"; exit 3; }
AN="$WORK/analyse_scorer_vs_labels.py"
export INK_METRIC_KEEP_PROB=1

for S in $SEGS; do
  D=$WORK/$S; mkdir -p "$D"
  cp -a "$MESHES/$S/mesh" "$D/mesh" || { say "MESH_COPY_FAILED $S"; exit 1; }
  "$PY" "$AN" labels "$S" "$D/labels_L3.npy" >> "$D/prep.log" 2>&1 || { say "LABELS_FAILED $S"; exit 1; }
  for MODE in linear smooth; do
    T=$D/${MODE}_tif; mkdir -p "$T"
    EXTRA=(); [ "$MODE" = smooth ] && EXTRA=(--surface-interpolation smooth)
    G=$(du -s --block-size=1G "$VCHOME" | cut -f1)
    [ "$G" -le "$DISK_GUARD_GB" ] || { say "DISK_GUARD ${G}GB"; exit 4; }
    say "RENDER $S $MODE"
    docker run --rm --user "$(id -u):$(id -g)" --memory 24g -e HOME="$VCHOME" \
      -v /home/jon/openclaw-workspace:/home/jon/openclaw-workspace \
      --entrypoint vc_render_tifxyz "$IMG" --volume "$WORK/inkcache" --remote-url "$INK_URL" \
      --group-idx 1 --scale 0.25 --scale-segmentation 1 --segmentation "$D/mesh" \
      --num-slices 5 --cache-gb 16 --tif-output "$T" "${EXTRA[@]}" > "$D/$MODE.render.log" 2>&1 \
      || { say "RENDER_FAILED $S $MODE"; exit 1; }
    grep -q "all slices exist, skipping" "$D/$MODE.render.log" && { say "SKIPPED $S $MODE"; exit 1; }
    if [ "$MODE" = smooth ]; then
      grep -q "Surface interpolation: smooth" "$D/$MODE.render.log" || { say "SMOOTH_NOT_ENGAGED $S"; exit 1; }
    else
      grep -q "Surface interpolation: smooth" "$D/$MODE.render.log" && { say "SMOOTH_IN_LINEAR $S"; exit 1; }
    fi
    "$PY" "$AN" strip "$D/$MODE" "$T" >> "$D/prep.log" 2>&1 || { say "STRIP_FAILED $S $MODE"; exit 1; }
    "$HERE/score_arms.sh" "$D/$MODE" > "$D/$MODE.score.log" 2>&1 || { say "SCORE_FAILED $S $MODE"; exit 1; }
    [ -f "$D/$MODE/ink_metric/predictions/seg_flat_prob.npy" ] || { say "NO_PROB $S $MODE"; exit 1; }
    rm -rf "$T"
    say "DONE $S $MODE"
  done
done
say "SC_CHAIN_DONE"
