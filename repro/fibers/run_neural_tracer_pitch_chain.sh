#!/usr/bin/env bash
# docs/preregistration/2026-10-19_neural_tracer_training_pitch.md -- finding 91's run of villa's neural fiber tracer
# (villa #2045, scrollprize/fiber_single_small at 4511825, volume mode, defaults), repeated on each ScrollGT cube
# resampled from 7.91 um to 9.6 um, the pitch of its Scroll 1 training source. Per cube: resample the CT and
# fiber_hz_vt's probability (scripts/resample_cube_pitch.py), build the presence level from the resampled probability
# (scripts/make_tracer_presence.py), trace with finding 91's flags but --base-um 9.6 and the resampled box, then
# score (scripts/neural_tracer_pitch_analysis.py). The scripts are frozen into $W on the first launch; a resume
# refuses if the repository's copies have changed. Refuses to start while the autoresearch loop or another GPU job
# runs. A cube that fails is recorded and skipped. Resumable: a cube with a fibers.afv is skipped.
# Environment: setup_neural_tracer_env.sh. Launch detached: setsid nohup bash <this> > $T/pitch_launch.log 2>&1 &
set -uo pipefail
# The checkout whose scripts run: the registered commit (a worktree until it merges). The loop runs in LOOPDIR.
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
LOOPDIR="${LOOPDIR:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
W="${W:-$T/pitch_run}"
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
HELDOUT="${HELDOUT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_heldout}"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
CUBES="s1_00497_01497_03997_256 s1_00497_02497_02997_256 s1_00997_02497_02997_256 s1_08997_02997_02497_256
s1_10997_02997_02997_256 s5_03997_01497_03997_256 s5_07997_02997_05497_256 s5_14997_01497_01497_256
s5_06494_01994_03994_512 s5_06994_00994_04994_512 s5_07994_01994_05494_512
s5_13497_01497_02497_256 s5_16997_03997_04497_256
s3_00994_00494_01994_512 s3_00994_01994_00494_512 s3_00994_02494_01494_512 s3_01994_01494_00994_512
s3_01994_01994_01494_512 s3_02994_02494_01994_512 s3_03494_01494_00494_512 s3_04494_00994_01494_512"
mkdir -p "$W" "$T/ct_9p6" "$T/prob_9p6" "$T/presence_9p6"
LOG=$W/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }
"$PY" "$LOOPDIR/scripts/loop_control.py" status --repo "$LOOPDIR" > /dev/null \
  && { say "SC_ABORTED the autoresearch loop is running"; exit 3; }
for p in /proc/[0-9]*; do
  [ "$p" = "/proc/$$" ] && continue
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -qE "tracers\.fibers\.tracing\.volume|f1_noise_probe" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
for f in neural_tracer_pitch_analysis.py neural_tracer_analysis.py afv_generator_analysis.py afv_to_labels.py \
         make_tracer_presence.py resample_cube_pitch.py; do
  if [ -e "$W/$f" ]; then
    cmp -s "$REPO/scripts/$f" "$W/$f" || { say "SC_ABORTED $f differs from the copy frozen in $W"; exit 3; }
  else
    cp "$REPO/scripts/$f" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
  fi
done
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD) villa $(git -C "$T/villa" rev-parse --short HEAD)"
for C in $CUBES; do
  [ -f "$W/$C/fibers.afv" ] && { say "SKIP_DONE $C"; continue; }
  N=${C##*_}
  # The resampled side: 212 for a 256^3 cube, 422 for a 512^3 one; the trace grid is half of it.
  NR=$("$PY" -c "import sys; sys.path.insert(0, sys.argv[1]); import resample_cube_pitch as r; print(r.resampled_length($N, 9.6 / r.FROM_UM))" "$W")
  NG=$((NR / 2))
  PROB="$REPO/local_data/fiber_skeletons/${C}_fiberprob.npy"
  [ -f "$PROB" ] || PROB="$HELDOUT/data/${C}_fiberprob.npy"
  if [ ! -e "$T/ct_9p6/$C.zarr/0" ] || [ ! -f "$T/prob_9p6/${C}_fiberprob.npy" ]; then
    # Each output is written whole (built aside, renamed) and kept if present.
    "$PY" "$W/resample_cube_pitch.py" --ct "$G/zarr/$C.zarr" --prob "$PROB" --out-ct "$T/ct_9p6/$C.zarr" \
      --out-prob "$T/prob_9p6/${C}_fiberprob.npy" > "$W/$C.resample.log" 2>&1 || { say "FAILED $C resample"; continue; }
  fi
  if [ ! -d "$T/presence_9p6/${C}_presence.zarr/1" ]; then
    "$PY" "$W/make_tracer_presence.py" "$T/prob_9p6/${C}_fiberprob.npy" "$T/presence_9p6/${C}_presence.zarr" \
      > "$W/$C.presence.log" 2>&1 || { say "FAILED $C presence"; continue; }
  fi
  "$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import make_tracer_presence as m; sys.exit(not m.level_complete(sys.argv[2]))' \
    "$W" "$T/presence_9p6/${C}_presence.zarr/1" || { say "FAILED $C presence incomplete"; continue; }
  say "TRACE $C (resampled $NR, grid $NG)"
  ( cd "$W" && HF_HUB_OFFLINE=1 "$TPY" -m vesuvius.neural_tracing.tracers.fibers.tracing.volume \
      --checkpoint "$CKPT" --ct "$T/ct_9p6/$C.zarr" --ct-level 0 --ct-grid-scale 1 --grid-scale 2 \
      --presence "$T/presence_9p6/${C}_presence.zarr/1" --box "0,0,0,$NG,$NG,$NG" --base-um 9.6 \
      --afv-template "$G/run/$C.afv" --out "$W/$C" ) > "$W/$C.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/$C/fibers.afv" ]; then say "DONE $C"; else say "FAILED $C rc=$rc"; fi
done
say "CHAIN_COMPLETE"
( cd "$REPO" && "$PY" "$W/neural_tracer_pitch_analysis.py" --work "$W" --out "$W/result.json" ) > "$W/analysis.log" 2>&1
say "ANALYSIS rc=$?"
