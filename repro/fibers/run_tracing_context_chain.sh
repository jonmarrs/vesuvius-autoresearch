#!/usr/bin/env bash
# WITHDRAWN 2026-10-24, never run: see the registration's last section. A run now is outside any registration.
# docs/preregistration/2026-10-23_tracing_context.md -- run both tracers on the 24 octants of the three in-sample 512^3
# cubes as cubes in their own right: our tracer by `bench_cli trace` at finding 80's published defaults (which runs the
# mask model on the octant, as on every real cube), then villa's neural tracer (villa #2045,
# scrollprize/fiber_single_small at 4511825) with finding 91's settings, its presence built from the probability
# bench_cli just cached. First the identity smoke: the same path on the real cube s5_07997_02997_05497_256 must
# reproduce the published probability, finding 94's labelling and finding 91's .afv (scripts/tracing_context.py smoke),
# or no octant runs. The scripts are frozen into $W on the first launch; a resume refuses if the repository's copies
# have changed. Refuses to start while the autoresearch loop or another GPU job runs. An octant that fails is recorded
# and skipped. Resumable: a step whose output exists is skipped. Tracing only: score afterwards, with the loop
# running, by
#   (cd $REPO && nice -n 19 .venv/bin/python $W/tracing_context.py score --work $W)
# Environment: setup_neural_tracer_env.sh (finding 91's venv, villa checkout and cached checkpoint).
# Launch detached: setsid nohup bash <this> > $T/context_launch.log 2>&1 &
set -uo pipefail
# The checkout whose scripts run: the registered commit (a worktree until it merges). The loop runs in LOOPDIR.
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
LOOPDIR="${LOOPDIR:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
# The shared venv's editable install resolves the package from the main checkout; this pins it to $REPO's, the
# registered commit, for bench_cli and the scripts alike.
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
W="${W:-$T/context_run}"
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
SMOKE=s5_07997_02997_05497_256
mkdir -p "$W/tracer" "$W/neural" "$W/presence"
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
for f in tracing_context.py octant_crop_rescore.py tolerance4_rescore.py neural_tracer_analysis.py \
         afv_generator_analysis.py afv_to_labels.py make_tracer_presence.py; do
  if [ -e "$W/$f" ]; then
    cmp -s "$REPO/scripts/$f" "$W/$f" || { say "SC_ABORTED $f differs from the copy frozen in $W"; exit 3; }
  else
    cp "$REPO/scripts/$f" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
  fi
done
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD) villa $(git -C "$T/villa" rev-parse --short HEAD)"
( cd "$REPO" && "$PY" "$W/tracing_context.py" prepare --work "$W" ) > "$W/prepare.log" 2>&1 \
  || { say "SC_ABORTED prepare"; exit 3; }

# run STEM PARENT: our tracer (and the mask model) on the stand-in cube, then the neural tracer on its CT.
run() {
  local c=$1 parent=$2
  if [ ! -f "$W/tracer/${c}_instances.npy" ]; then
    say "TRACE ours $c"
    ( cd "$REPO" && "$PY" -m vesuvius_autoresearch.fibers.bench_cli --data-dir "$W/data" trace --cube "$c" \
        --device cuda --save-instances "$W/tracer/${c}_instances.npy" --json-out "$W/tracer/${c}_trace.json" ) \
      > "$W/tracer/$c.log" 2>&1 || { say "FAILED ours $c rc=$?"; return 1; }
  fi
  if [ ! -d "$W/presence/${c}_presence.zarr/1" ]; then
    "$PY" "$W/make_tracer_presence.py" "$W/data/${c}_fiberprob.npy" "$W/presence/${c}_presence.zarr" \
      > "$W/presence/$c.log" 2>&1 || { say "FAILED $c presence"; return 1; }
  fi
  "$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import make_tracer_presence as m; sys.exit(not m.level_complete(sys.argv[2]))' \
    "$W" "$W/presence/${c}_presence.zarr/1" || { say "FAILED $c presence incomplete"; return 1; }
  [ -f "$W/neural/$c/fibers.afv" ] && return 0
  say "TRACE neural $c"
  # Offline: the pinned revision is already in the Hugging Face cache and cannot move mid-run.
  ( cd "$W" && HF_HUB_OFFLINE=1 "$TPY" -m vesuvius.neural_tracing.tracers.fibers.tracing.volume \
      --checkpoint "$CKPT" --ct "$W/ct/$c.zarr" --ct-level 0 --ct-grid-scale 1 --grid-scale 2 \
      --presence "$W/presence/${c}_presence.zarr/1" --box "0,0,0,128,128,128" --base-um 7.91 \
      --afv-template "$G/run/$parent.afv" --out "$W/neural/$c" ) > "$W/neural/$c.log" 2>&1
  local rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/neural/$c/fibers.afv" ]; then say "DONE $c"; else say "FAILED neural $c rc=$rc"; return 1; fi
}

run "$SMOKE" "$SMOKE" || { say "SMOKE_FAILED the smoke cube did not run: no octant runs"; exit 4; }
( cd "$REPO" && "$PY" "$W/tracing_context.py" smoke --work "$W" ) >> "$LOG" 2>&1 \
  || { say "SMOKE_FAILED the path does not reproduce the published runs: no octant runs"; exit 4; }
say "SMOKE_OK"

# shellcheck disable=SC2207
LINES=($( cd "$REPO" && "$PY" "$W/tracing_context.py" stems | tr ' ' ':' )) || { say "SC_ABORTED stems"; exit 3; }
for L in "${LINES[@]}"; do
  run "${L%%:*}" "${L##*:}"
done
say "CHAIN_COMPLETE"
