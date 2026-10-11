#!/usr/bin/env bash
# docs/preregistration/2026-10-11_fiber_heldout_split.md -- run fiber_hz_vt and our tracer (finding 80's published
# defaults) on the 10 villa Dataset004 fiber cubes the mask never trained on, then score them
# (scripts/fiber_heldout_analysis.py, frozen into $W at start). A cube that fails is recorded and skipped.
# Resumable: a cube with saved instances is skipped. Launch detached: setsid nohup bash <this> > $W/launch.log 2>&1 &
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
SRC="${SRC:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_d004/heldout}"
D="${D:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_heldout/data}"
W="${W:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_heldout/run}"
CUBES="s5_13497_01497_02497_256 s5_16997_03997_04497_256
s3_00994_00494_01994_512 s3_00994_01994_00494_512 s3_00994_02494_01494_512 s3_01994_01494_00994_512
s3_01994_01994_01494_512 s3_02994_02494_01994_512 s3_03494_01494_00494_512 s3_04494_00994_01494_512"
mkdir -p "$D" "$W"
LOG=$W/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }
for p in /proc/[0-9]*; do
  [ "$p" = "/proc/$$" ] && continue
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -qE "bench_cli (trace|score|floors)|get_ink_metrics.py" && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
cp "$REPO/scripts/fiber_heldout_analysis.py" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
# bench_cli reads <stem>.nml, <stem>_image.tif (and caches <stem>_fiberprob.npy) from one data dir.
for C in $CUBES; do
  IFS=_ read -r s z y x n <<< "$C"
  nml=$(ls "$SRC"/fibers_"${s}"*_"${z}"z_"${y}"y_"${x}"x_"${n}"_v*.nml 2>/dev/null | head -1)
  [ -n "$nml" ] || { say "SC_ABORTED no NML for $C"; exit 3; }
  ln -sfn "$nml" "$D/$C.nml"
  ln -sfn "$SRC/${C}_image.tif" "$D/${C}_image.tif"
  ln -sfn "$SRC/${C}_semantic.tif" "$D/${C}_semantic.tif"
done
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD)"
for C in $CUBES; do
  [ -f "$W/${C}_instances.npy" ] && { say "SKIP_DONE $C"; continue; }
  EXTRA=""
  case "$C" in *_512) EXTRA="--detect-block 128" ;; esac
  say "TRACE $C $EXTRA"
  ( cd "$REPO" && "$PY" -m vesuvius_autoresearch.fibers.bench_cli --data-dir "$D" trace --cube "$C" --device cuda \
      --save-instances "$W/${C}_instances.npy" --json-out "$W/${C}_trace.json" $EXTRA ) > "$W/$C.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/${C}_instances.npy" ]; then say "DONE $C"; else say "FAILED $C rc=$rc"; fi
done
say "CHAIN_COMPLETE"
( cd "$REPO" && "$PY" "$W/fiber_heldout_analysis.py" --data-dir "$D" --work "$W" --out "$W/result.json" ) > "$W/analysis.log" 2>&1
say "ANALYSIS rc=$?"
