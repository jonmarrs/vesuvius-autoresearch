#!/usr/bin/env bash
# docs/preregistration/2026-10-02_surface_interpolation_windows.md -- 8 full-height windows of
# detfit_up1's flat, each rendered by vc-render:sampler-f637f3b35 at the default (linear) and with
# --surface-interpolation smooth, then strip-built and scored like render_ink.py + get_ink_metrics.py.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
# Launch through run_snapshot.sh. Helpers are frozen into $OUT at start: the first launch died when a
# rebase briefly removed scripts/analyse_interp_windows.py from the working tree mid-run.
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
OUT=$SO/interp_windows
FLAT=$SO/detfit_up1/meshes/concat/w120-129_flat
IMG=vc-render:sampler-f637f3b35
SHA=f637f3b35208bafa7812b4d97fea45bf43d19edb
VCHOME=$SO/interp_smoke/vchome   # chunk cache from the smoke; same URL, content-addressed
INK_URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr"
FLAT_MD5_EXPECT=bfd9ef809c27930d553b778adc209dd9
DISK_GUARD_GB=200
say() { echo "$*  $(date -Is)"; }

for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && { say "WIN_ABORTED a render is running"; exit 3; }; done
[ -e "$OUT" ] && { say "WIN_ABORTED $OUT exists"; exit 5; }
[ "$(docker run --rm --entrypoint cat $IMG /opt/vcsrc/SAMPLER_SHA)" = "$SHA" ] || { say "WIN_ABORTED image sha"; exit 3; }
[ "$(cat "$FLAT"/[xyz].tif | md5sum | cut -d' ' -f1)" = "$FLAT_MD5_EXPECT" ] || { say "WIN_ABORTED flat md5"; exit 3; }
mkdir -p "$OUT" "$VCHOME"
cp "$REPO/scripts/analyse_interp_windows.py" "$OUT/analyse_interp_windows.py" || { say "WIN_ABORTED freeze"; exit 3; }
ANALYSE="$OUT/analyse_interp_windows.py"
[ -x "$HERE/score_arms.sh" ] && [ -f "$HERE/artifacts.py" ] || { say "WIN_ABORTED helpers missing in $HERE"; exit 3; }
mapfile -t XS < <("$PY" "$ANALYSE" select)
[ "${#XS[@]}" -eq 8 ] || { say "WIN_ABORTED expected 8 windows, got ${#XS[@]}"; exit 3; }
printf '%s\n' "${XS[@]}" > "$OUT/WINDOWS"
say "WINDOWS ${XS[*]}"

for X in "${XS[@]}"; do
  for MODE in linear smooth; do
    D=$OUT/w$X/$MODE; mkdir -p "$D/tif"
    EXTRA=(); [ "$MODE" = smooth ] && EXTRA=(--surface-interpolation smooth)
    G=$(du -s --block-size=1G "$VCHOME" | cut -f1)
    [ "$G" -le "$DISK_GUARD_GB" ] || { say "DISK_GUARD ${G}GB"; exit 4; }
    say "RENDER w$X $MODE"
    docker run --rm --user "$(id -u):$(id -g)" --memory 24g -e HOME="$VCHOME" \
      -v /home/jon/openclaw-workspace:/home/jon/openclaw-workspace \
      --entrypoint vc_render_tifxyz "$IMG" --scale-segmentation 4 \
      --segmentation "$FLAT" --scale 0.25 --group-idx 1 --volume "$SO/interp_smoke/inkcache" \
      --tif-output "$D/tif" --num-slices 5 --remote-url "$INK_URL" \
      --crop-x "$X" --crop-y 0 --crop-width 2048 --crop-height 4460 "${EXTRA[@]}" > "$D/render.log" 2>&1 \
      || { say "RENDER_FAILED w$X $MODE"; exit 1; }
    grep -q "all slices exist, skipping" "$D/render.log" && { say "SKIPPED w$X $MODE"; exit 1; }
    if [ "$MODE" = smooth ]; then
      grep -q "Surface interpolation: smooth" "$D/render.log" || { say "SMOOTH_NOT_ENGAGED w$X"; exit 1; }
    else
      grep -q "Surface interpolation: smooth" "$D/render.log" && { say "SMOOTH_IN_LINEAR w$X"; exit 1; }
    fi
    "$PY" "$ANALYSE" strip "$D" "$D/tif" >> "$D/render.log" 2>&1 \
      || { say "STRIP_FAILED w$X $MODE"; exit 1; }
    "$HERE/score_arms.sh" "$D" > "$D/score.log" 2>&1 \
      || { say "SCORE_FAILED w$X $MODE"; exit 1; }
    say "DONE w$X $MODE"
  done
done
say "WIN_CHAIN_DONE"
