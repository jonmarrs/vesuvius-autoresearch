#!/usr/bin/env bash
# docs/preregistration/2026-10-23_neural_tracer_ct_context.md -- villa's neural fiber tracer (villa #2045,
# scrollprize/fiber_single_small at 4511825) on the five Scroll-5 256^3 cubes with 128 voxels of real CT around each,
# the box still the cube, everything else as finding 91 ran it. Prepare first, CPU and network, with the loop running:
#   (cd $REPO && .venv/bin/python scripts/neural_tracer_ct_context.py fetch --work $W)      # ~1.5 GB public download
#   (cd $REPO && .venv/bin/python scripts/neural_tracer_ct_context.py presence --work $W)
# Both must report every core identical, or this refuses. Then the identity smoke: finding 91's own command on
# s5_07997_02997_05497_256 must reproduce its fibers.afv point for point, or no padded cube runs. The scripts are
# frozen into $W on the first launch; a resume refuses if the repository's copies have changed. Refuses to start while
# the autoresearch loop or another GPU job runs. A cube that fails is recorded and skipped. Resumable: a run with a
# fibers.afv is skipped. Score afterwards, with the loop running:
#   (cd $REPO && nice -n 19 .venv/bin/python $W/neural_tracer_ct_context.py score --work $W)
# Launch detached: setsid nohup bash <this> > $T/ct_context_launch.log 2>&1 &
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
LOOPDIR="${LOOPDIR:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
# The shared venv's editable install resolves the package from the main checkout; this pins it to $REPO's, the
# registered commit.
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
W="${W:-$T/ct_context_run}"
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
SMOKE=s5_07997_02997_05497_256
CUBES="s5_03997_01497_03997_256 s5_07997_02997_05497_256 s5_14997_01497_01497_256 s5_13497_01497_02497_256
s5_16997_03997_04497_256"
mkdir -p "$W/neural" "$W/smoke"
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
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -qE "tracers\.fibers\.tracing\.volume|bench_cli (trace|score|floors)|f1_noise_probe" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
for f in neural_tracer_ct_context.py neural_tracer_boundary.py tolerance4_rescore.py neural_tracer_analysis.py \
         afv_generator_analysis.py afv_to_labels.py; do
  if [ -e "$W/$f" ]; then
    cmp -s "$REPO/scripts/$f" "$W/$f" || { say "SC_ABORTED $f differs from the copy frozen in $W"; exit 3; }
  else
    cp "$REPO/scripts/$f" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
  fi
done
"$PY" -c 'import json, sys; p = json.load(open(sys.argv[1])); ok = all(r["core_equals_finding_85"] for r in p["ct"].values()) and all(r["core_equals_finding_91"] for r in p["presence"].values()) and len(p["ct"]) == len(p["presence"]) == 5; sys.exit(not ok)' \
  "$W/prepared.json" || { say "SC_ABORTED prepare (fetch, presence) incomplete or a core differs"; exit 3; }
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD) villa $(git -C "$T/villa" rev-parse --short HEAD)"

# trace OUT CT PRESENCE BOX TEMPLATE: finding 91's command with these four inputs.
trace() {
  ( cd "$W" && HF_HUB_OFFLINE=1 "$TPY" -m vesuvius.neural_tracing.tracers.fibers.tracing.volume \
      --checkpoint "$CKPT" --ct "$2" --ct-level 0 --ct-grid-scale 1 --grid-scale 2 \
      --presence "$3" --box "$4" --base-um 7.91 --afv-template "$5" --out "$1" ) > "$1.log" 2>&1
}

if [ ! -f "$W/smoke/$SMOKE/fibers.afv" ]; then
  say "SMOKE $SMOKE"
  trace "$W/smoke/$SMOKE" "$T/ct/$SMOKE.zarr" "$T/presence/${SMOKE}_presence.zarr/1" "0,0,0,128,128,128" "$G/run/$SMOKE.afv"
fi
( cd "$REPO" && "$PY" "$W/neural_tracer_ct_context.py" smoke --work "$W" ) >> "$LOG" 2>&1 \
  || { say "SMOKE_FAILED finding 91's command does not reproduce its run: no padded cube runs"; exit 4; }
say "SMOKE_OK"

for C in $CUBES; do
  [ -f "$W/neural/$C/fibers.afv" ] && { say "SKIP_DONE $C"; continue; }
  say "TRACE $C"
  trace "$W/neural/$C" "$W/ct/$C.zarr" "$W/presence/${C}_presence.zarr/1" "64,64,64,192,192,192" "$G/run/$C.afv"
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/neural/$C/fibers.afv" ]; then say "DONE $C"; else say "FAILED $C rc=$rc"; fi
done
say "CHAIN_COMPLETE"
