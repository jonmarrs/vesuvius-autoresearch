#!/usr/bin/env bash
# Reachability smoke for villa #1818 (vc_render_tifxyz --surface-interpolation), before any study.
#
# One 2048x1024 crop of detfit_up1's saved flat, sampled exactly as render_ink.py samples it
# (--scale 0.25 --group-idx 1 --num-slices 5, wrapper --scale-segmentation 4, remote ink zarr):
#   A  vc-render:sampler-75c79ac5f   (source build BEFORE #1818)        default
#   B  vc-render:sampler-f637f3b35   (source build AFTER #1818 + #1905) default (= linear)
#   C  vc-render:sampler-f637f3b35                                       --surface-interpolation smooth
# Compared by scripts/compare_interp_smoke.py, also against the same window of the PR #1905 build's
# full render of this flat (spiral_out/tif_score_pr1905), which checks the crop coordinates.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
OUT=$SO/interp_smoke
FLAT=$SO/detfit_up1/meshes/concat/w120-129_flat
INK_URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr"
CROP=(--crop-x 59392 --crop-y 1536 --crop-width 2048 --crop-height 1024)
say() { echo "$*  $(date -Is)"; }

[ -e "$OUT" ] && { say "SMOKE_ABORTED $OUT exists"; exit 5; }
mkdir -p "$OUT/vchome" "$OUT/inkcache"
cat "$FLAT"/[xyz].tif | md5sum | cut -d' ' -f1 > "$OUT/FLAT_MD5"

run() {  # name image extra-args...
  local name=$1 img=$2; shift 2
  mkdir -p "$OUT/$name"
  docker run --rm --entrypoint cat "$img" /opt/vcsrc/SAMPLER_SHA > "$OUT/$name.SAMPLER_SHA" 2>/dev/null
  say "RUN $name ($img $*)"
  /usr/bin/time -v docker run --rm --user "$(id -u):$(id -g)" --memory 24g -e HOME="$OUT/vchome" \
    -v /home/jon/openclaw-workspace:/home/jon/openclaw-workspace \
    --entrypoint vc_render_tifxyz "$img" --scale-segmentation 4 \
    --segmentation "$FLAT" --scale 0.25 --group-idx 1 --volume "$OUT/inkcache" \
    --tif-output "$OUT/$name" --num-slices 5 --remote-url "$INK_URL" "${CROP[@]}" "$@" \
    > "$OUT/$name.log" 2>&1
  local rc=$?
  grep -q "all slices exist, skipping" "$OUT/$name.log" && { say "SKIPPED $name"; exit 1; }
  [ $rc -eq 0 ] || { say "RUN_FAILED $name rc=$rc"; exit 1; }
  say "DONE $name: $(ls "$OUT/$name" | wc -l) tif(s)"
}

run A vc-render:sampler-75c79ac5f
run B vc-render:sampler-f637f3b35
run C vc-render:sampler-f637f3b35 --surface-interpolation smooth
grep -q "Surface interpolation: smooth" "$OUT/C.log" || { say "SMOOTH_NOT_ENGAGED"; exit 1; }
say "SMOKE_DONE"
