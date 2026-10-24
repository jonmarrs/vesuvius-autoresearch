#!/usr/bin/env bash
# docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md -- villa's neural fiber tracer (villa #2045,
# scrollprize/fiber_single_small at 4511825, volume mode) with its seeding set per micrometre by
# scripts/neural_tracer_seeding.py, in two arms over the 21 ScrollGT cubes:
#   A: finding 92's 9.6 um cubes (ct_9p6/, presence_9p6/), seeded as natively: spacing flags and smoothing / r;
#   B: finding 91's native cubes (ct/, presence/), seeded as at 9.6 um: the same * r.
# First the identity smoke: the launcher at villa's default smoothing, on finding 91's repeat cube, must reproduce
# finding 91's fibers.afv point for point, or no arm runs. Every flag comes from
# `neural_tracer_seeding_analysis.py args`, so the chain passes exactly the registered values. The scripts are frozen
# into $W on the first launch; a resume refuses if the repository's copies have changed. Refuses to start while the
# autoresearch loop or another GPU job runs. A cube that fails is recorded and skipped. Resumable: a cube with a
# fibers.afv is skipped. Tracing only: score afterwards, with the loop running, by
#   (cd $REPO && nice -n 19 .venv/bin/python $W/neural_tracer_seeding_analysis.py score --work $W)
# Environment: setup_neural_tracer_env.sh (finding 91's inputs and finding 92's resampled ones must exist).
# Launch detached: setsid nohup bash <this> > $T/seeding_launch.log 2>&1 &
set -uo pipefail
# The checkout whose scripts run: the registered commit (a worktree until it merges). The loop runs in LOOPDIR.
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
LOOPDIR="${LOOPDIR:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
W="${W:-$T/seeding_run}"
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
SMOKE=s1_00497_01497_03997_256
CUBES="s1_00497_01497_03997_256 s1_00497_02497_02997_256 s1_00997_02497_02997_256 s1_08997_02997_02497_256
s1_10997_02997_02997_256 s5_03997_01497_03997_256 s5_07997_02997_05497_256 s5_14997_01497_01497_256
s5_06494_01994_03994_512 s5_06994_00994_04994_512 s5_07994_01994_05494_512
s5_13497_01497_02497_256 s5_16997_03997_04497_256
s3_00994_00494_01994_512 s3_00994_01994_00494_512 s3_00994_02494_01494_512 s3_01994_01494_00994_512
s3_01994_01994_01494_512 s3_02994_02494_01994_512 s3_03494_01494_00494_512 s3_04494_00994_01494_512"
mkdir -p "$W/identity" "$W/A" "$W/B"
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
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -qE "tracers\.fibers\.tracing\.volume|neural_tracer_seeding\.py|f1_noise_probe" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
for f in neural_tracer_seeding.py neural_tracer_seeding_analysis.py neural_tracer_pitch_analysis.py \
         neural_tracer_pitch_funnel.py neural_tracer_analysis.py afv_generator_analysis.py afv_to_labels.py \
         resample_cube_pitch.py; do
  if [ -e "$W/$f" ]; then
    cmp -s "$REPO/scripts/$f" "$W/$f" || { say "SC_ABORTED $f differs from the copy frozen in $W"; exit 3; }
  else
    cp "$REPO/scripts/$f" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
  fi
done
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD) villa $(git -C "$T/villa" rev-parse --short HEAD)"

# trace OUT CT PRESENCE GRID ARGS...: the launcher, then villa's own flags for one cube.
trace() {
  local out=$1 ct=$2 presence=$3 grid=$4 cube=$5; shift 5
  ( cd "$W" && HF_HUB_OFFLINE=1 "$TPY" "$W/neural_tracer_seeding.py" "$@" --checkpoint "$CKPT" --ct "$ct" \
      --ct-level 0 --ct-grid-scale 1 --grid-scale 2 --presence "$presence" --box "0,0,0,$grid,$grid,$grid" \
      --afv-template "$G/run/$cube.afv" --out "$out" ) > "$out.log" 2>&1
}

if [ ! -f "$W/identity/$SMOKE/fibers.afv" ]; then
  say "SMOKE $SMOKE"
  trace "$W/identity/$SMOKE" "$T/ct/$SMOKE.zarr" "$T/presence/${SMOKE}_presence.zarr/1" 128 "$SMOKE" \
    --smoothing 1.0 --base-um 7.91
fi
"$PY" "$W/neural_tracer_seeding_analysis.py" smoke --afv "$W/identity/$SMOKE/fibers.afv" \
  --reference "$T/run/$SMOKE/fibers.afv" >> "$LOG" 2>&1 \
  || { say "SMOKE_FAILED the launcher at the default does not reproduce finding 91: no arm runs"; exit 4; }
say "SMOKE_OK"

for ARM in A B; do
  # shellcheck disable=SC2207
  FLAGS=($("$PY" "$W/neural_tracer_seeding_analysis.py" args --arm "$ARM")) || { say "SC_ABORTED args $ARM"; exit 3; }
  for C in $CUBES; do
    [ -f "$W/$ARM/$C/fibers.afv" ] && { say "SKIP_DONE $ARM $C"; continue; }
    if [ "$ARM" = A ]; then CT="$T/ct_9p6/$C.zarr"; PRES="$T/presence_9p6/${C}_presence.zarr/1"
    else CT="$T/ct/$C.zarr"; PRES="$T/presence/${C}_presence.zarr/1"; fi
    [ -e "$CT/0/.zarray" ] && [ -d "$PRES" ] || { say "FAILED $ARM $C inputs missing"; continue; }
    NG=$("$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import neural_tracer_seeding_analysis as s; g = s.ARMS[sys.argv[2]]["grid"](sys.argv[3]); assert g == int(g); print(int(g))' "$W" "$ARM" "$C") \
      || { say "FAILED $ARM $C grid"; continue; }
    say "TRACE $ARM $C (grid $NG)"
    trace "$W/$ARM/$C" "$CT" "$PRES" "$NG" "$C" "${FLAGS[@]}"
    rc=$?
    if [ "$rc" -eq 0 ] && [ -f "$W/$ARM/$C/fibers.afv" ]; then say "DONE $ARM $C"; else say "FAILED $ARM $C rc=$rc"; fi
  done
done
say "CHAIN_COMPLETE"
