#!/usr/bin/env bash
# docs/preregistration/2026-10-25_neural_tracer_steep_heading.md -- villa's neural fiber tracer (villa #2045,
# scrollprize/fiber_single_small at 4511825) on all 21 cubes with the scan around each, findings 97 and 98's inputs and
# command, through scripts/neural_tracer_heading_arm.py: the seed dots villa skips where its CT axis lies more than 35
# degrees from the presence direction are traced, from the presence direction projected into the CT's sheet (`sheet`)
# or from villa's own CT axis (`keep`). Nothing is fetched: the CT and presence are findings 97 and 98's.
# First the identity smoke: the launcher's `villa` arm on SMOKE must reproduce finding 97's run point for point, or no
# arm runs. Then sheet and keep on the ten held-out cubes, then on the eleven in-sample ones. The scripts are frozen
# into $W on the first launch; a resume refuses if the repository's copies have changed. Refuses to start while the
# autoresearch loop or another GPU job runs. A run that fails is recorded and skipped. Resumable: a run with a
# fibers.afv is skipped. Score afterwards, with the loop running:
#   (cd $REPO && nice -n 19 .venv/bin/python $W/neural_tracer_steep_heading.py score --work $W)
# Launch detached: setsid nohup bash <this> > $T/steep_heading_launch.log 2>&1 &
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
LOOPDIR="${LOOPDIR:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
W="${W:-$T/steep_heading_run}"
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
SMOKE=s5_13497_01497_02497_256
HELD="s5_13497_01497_02497_256 s5_16997_03997_04497_256 s3_00994_00494_01994_512 s3_00994_01994_00494_512
s3_00994_02494_01494_512 s3_01994_01494_00994_512 s3_01994_01994_01494_512 s3_02994_02494_01994_512
s3_03494_01494_00494_512 s3_04494_00994_01494_512"
IN_SAMPLE="s5_03997_01497_03997_256 s5_07997_02997_05497_256 s5_14997_01497_01497_256 s1_00497_01497_03997_256
s1_00497_02497_02997_256 s1_00997_02497_02997_256 s1_08997_02997_02497_256 s1_10997_02997_02997_256
s5_06494_01994_03994_512 s5_06994_00994_04994_512 s5_07994_01994_05494_512"
mkdir -p "$W/sheet" "$W/keep" "$W/smoke"
LOG=$W/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }
# Only 1 means nothing is running: 0 is a running loop, and 2 (or a missing interpreter) means loop_control cannot
# tell, as when the lock is held without a valid PID.
"$PY" "$LOOPDIR/scripts/loop_control.py" status --repo "$LOOPDIR" > /dev/null
case $? in
  1) ;;
  0) say "SC_ABORTED the autoresearch loop is running"; exit 3 ;;
  *) say "SC_ABORTED loop_control.py status cannot tell whether the autoresearch loop is running"; exit 3 ;;
esac
for p in /proc/[0-9]*; do
  [ "$p" = "/proc/$$" ] && continue
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null \
    | grep -qE "tracers\.fibers\.tracing\.volume|neural_tracer_heading_arm|bench_cli (trace|score|floors)|f1_noise_probe" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
for f in neural_tracer_heading_arm.py neural_tracer_steep_heading.py neural_tracer_ct_context_512.py \
         neural_tracer_ct_context.py neural_tracer_boundary.py tolerance4_rescore.py neural_tracer_analysis.py \
         afv_generator_analysis.py afv_to_labels.py raw_tiff_region.py; do
  if [ -e "$W/$f" ]; then
    cmp -s "$REPO/scripts/$f" "$W/$f" || { say "SC_ABORTED $f differs from the copy frozen in $W"; exit 3; }
  else
    cp "$REPO/scripts/$f" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
  fi
done
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD) villa $(git -C "$T/villa" rev-parse --short HEAD)"

# trace ARM OUT CUBE: findings 97 and 98's command on their inputs, through the launcher.
trace() {
  local size=${3##*_} base
  if [ "$size" = 256 ]; then base=$T/ct_context_run; box=64,64,64,192,192,192
  else base=$T/ct_context_512_run; box=64,64,64,320,320,320; fi
  ( cd "$W" && HF_HUB_OFFLINE=1 "$TPY" "$W/neural_tracer_heading_arm.py" --arm "$1" \
      --checkpoint "$CKPT" --ct "$base/ct/$3.zarr" --ct-level 0 --ct-grid-scale 1 --grid-scale 2 \
      --presence "$base/presence/${3}_presence.zarr/1" --box "$box" --base-um 7.91 --afv-template "$G/run/$3.afv" \
      --out "$2" ) > "$2.log" 2>&1
}

if [ ! -f "$W/smoke/$SMOKE/fibers.afv" ]; then
  say "SMOKE $SMOKE"
  trace villa "$W/smoke/$SMOKE" "$SMOKE"
fi
( cd "$REPO" && "$PY" "$W/neural_tracer_steep_heading.py" smoke --work "$W" ) >> "$LOG" 2>&1 \
  || { say "SMOKE_FAILED the launcher's villa arm does not reproduce finding 97's run: no arm runs"; exit 4; }
say "SMOKE_OK"

for SET in HELD IN_SAMPLE; do
  for ARM in sheet keep; do
    for C in ${!SET}; do
      [ -f "$W/$ARM/$C/fibers.afv" ] && { say "SKIP_DONE $ARM $C"; continue; }
      say "TRACE $ARM $C"
      trace "$ARM" "$W/$ARM/$C" "$C"
      rc=$?
      if [ "$rc" -eq 0 ] && [ -f "$W/$ARM/$C/fibers.afv" ]; then say "DONE $ARM $C"; else say "FAILED $ARM $C rc=$rc"; fi
    done
  done
done
say "CHAIN_COMPLETE"
