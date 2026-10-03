#!/usr/bin/env bash
# docs/preregistration/2026-10-03_surface_interpolation_vs_labels.md -- 8 labelled Scroll-1 segments, each
# rendered whole from the 3D ink prediction in linear and smooth mode (vc-render:sampler-f637f3b35), max over
# 16 slices, kept for scripts/analyse_interp_vs_labels.py. Launch through run_snapshot.sh; the analysis
# helper is frozen into the work dir at start.
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
WORK=$SO/gt_interp/study
IMG=vc-render:sampler-f637f3b35
SHA=f637f3b35208bafa7812b4d97fea45bf43d19edb
VCHOME=$SO/interp_smoke/vchome
B=https://vesuvius-challenge-open-data.s3.amazonaws.com
INK_URL="$B/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr"
SEGS="20230702185753 20230929220926 20231007101619 20231012184424 20231016151002 20231031143852 20231106155351 20231210121321"
DISK_GUARD_GB=300
say() { echo "$*  $(date -Is)"; }

for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && { say "GT_ABORTED a render is running"; exit 3; }; done
[ -e "$WORK" ] && { say "GT_ABORTED $WORK exists"; exit 5; }
[ "$(docker run --rm --entrypoint cat $IMG /opt/vcsrc/SAMPLER_SHA)" = "$SHA" ] || { say "GT_ABORTED image sha"; exit 3; }
mkdir -p "$WORK" "$WORK/inkcache"
cp "$REPO/scripts/analyse_interp_vs_labels.py" "$WORK/analyse_interp_vs_labels.py" || { say "GT_ABORTED freeze"; exit 3; }
AN="$WORK/analyse_interp_vs_labels.py"

for S in $SEGS; do
  D=$WORK/$S; mkdir -p "$D/mesh"
  M=PHercParis4/segments/$S/mesh/$S-on-20260411134726-2.4um.tifxyz
  for f in meta.json x.tif y.tif z.tif; do
    curl -s -f -o "$D/mesh/$f" "$B/$M/$f" || { say "MESH_FETCH_FAILED $S $f"; exit 1; }
  done
  "$PY" "$AN" labels "$S" "$D/labels_L2.npy" >> "$D/prep.log" 2>&1 || { say "LABELS_FAILED $S"; exit 1; }
  for MODE in linear smooth; do
    T=$D/${MODE}_tif; mkdir -p "$T"
    EXTRA=(); [ "$MODE" = smooth ] && EXTRA=(--surface-interpolation smooth)
    G=$(du -s --block-size=1G "$VCHOME" | cut -f1)
    [ "$G" -le "$DISK_GUARD_GB" ] || { say "DISK_GUARD ${G}GB"; exit 4; }
    say "RENDER $S $MODE"
    docker run --rm --user "$(id -u):$(id -g)" --memory 24g -e HOME="$VCHOME" \
      -v /home/jon/openclaw-workspace:/home/jon/openclaw-workspace \
      --entrypoint vc_render_tifxyz "$IMG" --volume "$WORK/inkcache" --remote-url "$INK_URL" \
      --group-idx 2 --scale 1 --scale-segmentation 1 --segmentation "$D/mesh" \
      --num-slices 16 --slice-step 0.5 --cache-gb 16 --tif-output "$T" "${EXTRA[@]}" > "$D/$MODE.render.log" 2>&1 \
      || { say "RENDER_FAILED $S $MODE"; exit 1; }
    grep -q "all slices exist, skipping" "$D/$MODE.render.log" && { say "SKIPPED $S $MODE"; exit 1; }
    if [ "$MODE" = smooth ]; then
      grep -q "Surface interpolation: smooth" "$D/$MODE.render.log" || { say "SMOOTH_NOT_ENGAGED $S"; exit 1; }
    else
      grep -q "Surface interpolation: smooth" "$D/$MODE.render.log" && { say "SMOOTH_IN_LINEAR $S"; exit 1; }
    fi
    "$PY" "$AN" maxcomp "$D/${MODE}_max.tif" "$T" >> "$D/prep.log" 2>&1 || { say "MAXCOMP_FAILED $S $MODE"; exit 1; }
    rm -rf "$T"
    say "DONE $S $MODE"
  done
done
say "GT_CHAIN_DONE"
