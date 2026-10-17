#!/usr/bin/env bash
# docs/preregistration/2026-10-16_neural_fiber_tracer_entrant.md -- run villa's neural fiber tracer (villa #2045,
# scrollprize/fiber_single_small at 4511825) in volume mode at its defaults on the 21 ScrollGT fiber cubes, then
# score the .afv files (scripts/neural_tracer_analysis.py, frozen into $W at start). Environment:
# setup_neural_tracer_env.sh. A cube that fails is recorded and skipped. Resumable: a cube with a fibers.afv is
# skipped. Launch detached: setsid nohup bash <this> > $T/launch.log 2>&1 &
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
W="${W:-$T/run}"
# Finding 85: each cube's CT as a local Zarr array (written from the TIFF ScrollGT uses, read back identical), and
# #1934's .afv files, which are the frame templates here and the generator comparator.
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
HELDOUT="${HELDOUT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_heldout}"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
CUBES="s1_00497_01497_03997_256 s1_00497_02497_02997_256 s1_00997_02497_02997_256 s1_08997_02997_02497_256
s1_10997_02997_02997_256 s5_03997_01497_03997_256 s5_07997_02997_05497_256 s5_14997_01497_01497_256
s5_06494_01994_03994_512 s5_06994_00994_04994_512 s5_07994_01994_05494_512
s5_13497_01497_02497_256 s5_16997_03997_04497_256
s3_00994_00494_01994_512 s3_00994_01994_00494_512 s3_00994_02494_01494_512 s3_01994_01494_00994_512
s3_01994_01994_01494_512 s3_02994_02494_01994_512 s3_03494_01494_00494_512 s3_04494_00994_01494_512"
REPEAT="s3_00994_00494_01994_512 s1_00497_01497_03997_256"
mkdir -p "$W" "$T/ct" "$T/presence"
LOG=$W/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }
for p in /proc/[0-9]*; do
  [ "$p" = "/proc/$$" ] && continue
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -qE "tracers\.fibers\.tracing\.volume|f1_noise_probe" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
for f in neural_tracer_analysis.py afv_generator_analysis.py afv_to_labels.py make_tracer_presence.py; do
  cp "$REPO/scripts/$f" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
done
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD) villa $(git -C "$T/villa" rev-parse --short HEAD)"
for C in $CUBES; do
  [ -f "$W/$C/fibers.afv" ] && { say "SKIP_DONE $C"; continue; }
  N=${C##*_}
  NG=$((N / 2))
  # The tracer reads a local CT as <store>/<level>/.zarray: finding 85's array becomes level 0 of a group.
  if [ ! -e "$T/ct/$C.zarr/0" ]; then mkdir -p "$T/ct/$C.zarr" && ln -s "$G/zarr/$C.zarr" "$T/ct/$C.zarr/0"; fi
  PROB="$REPO/local_data/fiber_skeletons/${C}_fiberprob.npy"
  [ -f "$PROB" ] || PROB="$HELDOUT/data/${C}_fiberprob.npy"
  if [ ! -d "$T/presence/${C}_presence.zarr/1" ]; then
    "$PY" "$W/make_tracer_presence.py" "$PROB" "$T/presence/${C}_presence.zarr" > "$W/$C.presence.log" 2>&1 \
      || { say "FAILED $C presence"; continue; }
  fi
  say "TRACE $C"
  # Offline: the pinned revision is already in the Hugging Face cache and cannot move mid-run.
  ( cd "$W" && HF_HUB_OFFLINE=1 "$TPY" -m vesuvius.neural_tracing.tracers.fibers.tracing.volume \
      --checkpoint "$CKPT" --ct "$T/ct/$C.zarr" --ct-level 0 --ct-grid-scale 1 --grid-scale 2 \
      --presence "$T/presence/${C}_presence.zarr/1" --box "0,0,0,$NG,$NG,$NG" --base-um 7.91 \
      --afv-template "$G/run/$C.afv" --out "$W/$C" ) > "$W/$C.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/$C/fibers.afv" ]; then say "DONE $C"; else say "FAILED $C rc=$rc"; fi
done
# Run-to-run variation, descriptive: two cubes traced a second time, identically, into repeat/.
for C in $REPEAT; do
  [ -f "$W/repeat/$C/fibers.afv" ] && { say "SKIP_DONE repeat $C"; continue; }
  [ -f "$W/$C/fibers.afv" ] || { say "SKIP repeat $C (first run missing)"; continue; }
  N=${C##*_}
  NG=$((N / 2))
  mkdir -p "$W/repeat"
  say "REPEAT $C"
  ( cd "$W" && HF_HUB_OFFLINE=1 "$TPY" -m vesuvius.neural_tracing.tracers.fibers.tracing.volume \
      --checkpoint "$CKPT" --ct "$T/ct/$C.zarr" --ct-level 0 --ct-grid-scale 1 --grid-scale 2 \
      --presence "$T/presence/${C}_presence.zarr/1" --box "0,0,0,$NG,$NG,$NG" --base-um 7.91 \
      --afv-template "$G/run/$C.afv" --out "$W/repeat/$C" ) > "$W/repeat/$C.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/repeat/$C/fibers.afv" ]; then say "DONE repeat $C"; else say "FAILED repeat $C rc=$rc"; fi
done
say "CHAIN_COMPLETE"
( cd "$REPO" && "$PY" "$W/neural_tracer_analysis.py" --work "$W" --generator-work "$G/run" \
    --out "$W/result.json" ) > "$W/analysis.log" 2>&1
say "ANALYSIS rc=$?"
