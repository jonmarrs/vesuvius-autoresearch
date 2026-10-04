#!/usr/bin/env bash
# docs/preregistration/2026-10-02_surface_interpolation_windows.md -- 8 full-height windows of
# detfit_up1's flat, each rendered by vc-render:sampler-f637f3b35 at the default (linear) and with
# --surface-interpolation smooth, then strip-built and scored like render_ink.py + get_ink_metrics.py.
set -uo pipefail
export SO="${SO:-/home/jon/openclaw-workspace/Neo-VM/spiral_out}"
# Launch through run_snapshot.sh. Helpers are frozen into $OUT at start: the first launch died when a
# rebase briefly removed scripts/analyse_interp_windows.py from the working tree mid-run.
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
PY="${PY:-$REPO/.venv/bin/python}"
OUT=$SO/interp_windows
FLAT=$SO/detfit_up1/meshes/concat/w120-129_flat
IMG=vc-render:sampler-f637f3b35
SHA=f637f3b35208bafa7812b4d97fea45bf43d19edb
VCHOME=$SO/interp_smoke/vchome   # chunk cache from the smoke; same URL, content-addressed
INK_URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr"
FLAT_MD5_EXPECT=bfd9ef809c27930d553b778adc209dd9
DISK_GUARD_GB=200
say() { echo "$*  $(date -Is)"; }
check_flat() {
  local actual
  actual=$(cat "$FLAT/x.tif" "$FLAT/y.tif" "$FLAT/z.tif" | md5sum | cut -d' ' -f1) \
    || { say "WIN_ABORTED reading flat"; return 3; }
  [ "$actual" = "$FLAT_MD5_EXPECT" ] || { say "WIN_ABORTED flat md5"; return 3; }
}

for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && { say "WIN_ABORTED a render is running"; exit 3; }; done
[ -e "$OUT" ] && { say "WIN_ABORTED $OUT exists"; exit 5; }
[ "$(docker run --rm --entrypoint cat $IMG /opt/vcsrc/SAMPLER_SHA)" = "$SHA" ] || { say "WIN_ABORTED image sha"; exit 3; }
check_flat || exit 3
# Claim a new run atomically; another launch cannot overwrite its manifest.
mkdir "$OUT" || { say "WIN_ABORTED cannot create $OUT"; exit 5; }
mkdir -p "$VCHOME" || exit 3
cp "$REPO/scripts/analyse_interp_windows.py" "$REPO/scripts/interpolation_inputs.py" "$OUT/" \
  || { say "WIN_ABORTED freeze analysis"; exit 3; }
ANALYSE="$OUT/analyse_interp_windows.py"
[ -x "$HERE/score_arms.sh" ] && [ -f "$HERE/artifacts.py" ] || { say "WIN_ABORTED helpers missing in $HERE"; exit 3; }
cp "$HERE/score_arms.sh" "$HERE/artifacts.py" "$OUT/" || { say "WIN_ABORTED freeze scorer"; exit 3; }
# Process substitution hides the selector's exit code, even if it printed 8 rows
# before failing. Capture its status before accepting the manifest.
SELECTION=$("$PY" "$ANALYSE" select) || { say "WIN_ABORTED selection failed"; exit 3; }
mapfile -t XS <<< "$SELECTION"
[ "${#XS[@]}" -eq 8 ] || { say "WIN_ABORTED expected 8 windows, got ${#XS[@]}"; exit 3; }
for X in "${XS[@]}"; do [[ "$X" =~ ^[0-9]+$ ]] || { say "WIN_ABORTED invalid window: $X"; exit 3; }; done
printf '%s\n' "${XS[@]}" > "$OUT/WINDOWS" || exit 3
say "WINDOWS ${XS[*]}"

for X in "${XS[@]}"; do
  for MODE in linear smooth; do
    check_flat || exit 3
    D=$OUT/w$X/$MODE; mkdir -p "$D/tif" || exit 3
    EXTRA=(); [ "$MODE" = smooth ] && EXTRA=(--surface-interpolation smooth)
    G=$(du -s --block-size=1G "$VCHOME" | cut -f1) || { say "DISK_GUARD unavailable"; exit 4; }
    [ "$G" -le "$DISK_GUARD_GB" ] || { say "DISK_GUARD ${G}GB"; exit 4; }
    say "RENDER w$X $MODE"
    docker run --rm --user "$(id -u):$(id -g)" --memory 24g -e HOME="$VCHOME" \
      -v "$SO:$SO" \
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
    "$OUT/score_arms.sh" "$D" > "$D/score.log" 2>&1 \
      || { say "SCORE_FAILED w$X $MODE"; exit 1; }
    say "DONE w$X $MODE"
  done
done
say "WIN_CHAIN_DONE"
