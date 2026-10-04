#!/usr/bin/env bash
# docs/preregistration/2026-10-04_install_route_band_vs_labels.md -- metric preset, slice-step 0.5 / 1.0 / 2.0 on the 8
# labelled segments, rendered and compared with inkagree 0.2.2 (pinned, own venv). Launch via run_snapshot.sh.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
OUT=$SO/route_study
IMG=vc-render:sampler-f637f3b35
INKAGREE_REF=4add4cd   # 0.2.2 (0.2.1 lacked imagecodecs; see prereg amendment)
STEPS="0.5 1.0 2.0"
DISK_GUARD_GB=400
say() { echo "$*  $(date -Is)"; }

for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && { say "ROUTE_ABORTED a render is running"; exit 3; }; done
[ -e "$OUT" ] && { say "ROUTE_ABORTED $OUT exists"; exit 5; }
VCHOME=$SO/route_cache  # outside $OUT so a relaunch reuses streamed chunks
mkdir -p "$VCHOME" "$OUT/results"
uv venv -q -p 3.12 "$OUT/venv" || { say "ROUTE_ABORTED venv"; exit 3; }
VIRTUAL_ENV="$OUT/venv" uv pip install -q "git+https://github.com/jonmarrs/inkagree@$INKAGREE_REF" || { say "ROUTE_ABORTED install"; exit 3; }
IA="$OUT/venv/bin/inkagree"
[ "$("$IA" --version)" = "inkagree 0.2.2" ] || { say "ROUTE_ABORTED version $("$IA" --version)"; exit 3; }
mapfile -t SEGS < <("$IA" segments)
[ "${#SEGS[@]}" -eq 8 ] || { say "ROUTE_ABORTED expected 8 labelled segments, got ${#SEGS[@]}"; exit 3; }
printf '%s\n' "${SEGS[@]}" > "$OUT/SEGMENTS"
say "SEGMENTS ${SEGS[*]}"

for S in "${SEGS[@]}"; do
  D=$OUT/$S
  "$IA" fetch "$S" "$D" > /dev/null || { say "FETCH_FAILED $S"; exit 1; }
  for X in $STEPS; do
    G=$(du -s --block-size=1G "$VCHOME" | cut -f1)
    [ "$G" -le "$DISK_GUARD_GB" ] || { say "DISK_GUARD ${G}GB"; exit 4; }
    say "RENDER $S step $X"
    "$IA" render "$D" "$D/step$X.tif" --preset metric --image "$IMG" --cache-home "$VCHOME" -- --slice-step "$X" \
      > "$D/step$X.out" 2>&1 || { say "RENDER_FAILED $S $X"; exit 1; }
    head -1 "$D/step$X.render.log" | grep -q -- "--slice-step $X" || { say "STEP_NOT_APPLIED $S $X"; exit 1; }
  done
  for X in 0.5 2.0; do
    "$IA" compare "$S" "$D" "$D/step1.0.tif" "$D/step$X.tif" --level 3 --json "$OUT/results/${S}_step$X.json" \
      > "$OUT/results/${S}_step$X.txt" 2>&1
    rc=$?; [ "$rc" -le 2 ] || { say "COMPARE_FAILED $S $X rc=$rc"; exit 1; }  # 2 = not compared (recorded)
  done
  say "DONE $S"
done
for X in 0.5 2.0; do
  "$IA" summarize "$OUT"/results/*_step$X.json --k 6 --json "$OUT/results/summary_step$X.json" > "$OUT/results/summary_step$X.txt"
done
say "ROUTE_CHAIN_DONE"
