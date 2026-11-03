#!/usr/bin/env bash
# docs/preregistration/2026-11-02_seed_heading_confirmation.md -- villa's own volume tracer at VILLA_SHA, without
# (`before`) and with (`after`) repro/fibers/villa_volume_seed_heading.patch, on the ten fiber-skeletons cubes that
# ScrollGT does not ship, with finding 97's protocol, through scripts/seed_heading_confirmation.py.
# Before this chain, with the loop running, prepare the padded CT (CPU and network; resumable):
#   (cd $REPO && nice -n 19 .venv/bin/python scripts/seed_heading_confirmation.py fetch --work $W)
# The chain refuses to start unless $W/prepared.json shows all ten cores equal to Dataset004's images. It freezes the
# study's scripts and the patch into $W, makes the presence (fiber_hz_vt on the GPU), runs the smoke, then traces
# `before` and `after` on each cube. A run the log shows DONE is skipped on a resume. Afterwards, CPU only:
#   (cd $REPO && nice -n 19 .venv/bin/python $W/code/seed_heading_confirmation.py score --work $W)
# villa's source comes from VILLA_GIT, a checkout holding VILLA_SHA (git archive: its working tree is not read). It runs
# in finding 97's tracer environment ($T/venv) with that source first on PYTHONPATH, which the chain checks, and with
# villa's native vc_object_store from VC_SITE. DRY_RUN=1 prepares and checks the sources and imports, prints the trace
# commands and stops: no loop or GPU check, no presence, no trace.
# Refuses to start while the autoresearch loop or another GPU job runs. A lease prevents concurrent use of W.
# Failed or incomplete traces exit 1; setup refusals exit 3.
# Launch detached: setsid nohup bash <this> > $W.launch.log 2>&1 < /dev/null & disown
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
LOOPDIR="${LOOPDIR:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
VILLA_GIT="${VILLA_GIT:-/home/jon/openclaw-workspace/Neo-VM/projects/villa-current-39a8cf3a}"
VILLA_SHA=39a8cf3a124bdd5540ee826e1cb30047c8dc8c85  # registered; the re-run of 2026-10-28 reproduced findings 97 and 100
VC_SITE="${VC_SITE:-/home/jon/openclaw-workspace/Neo-VM/projects/villa-build-shims/site-vc-object-store}"
DRY_RUN="${DRY_RUN:-0}"
W="${W:-$T/seed_heading_confirmation}"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
CUBES="s1_02494_01494_03994_512 s1_08994_02494_03494_512 s1_09997_02497_03497_256 s5_05497_01997_02997_256
s5_05497_02497_02497_256 s5_08994_02994_03994_512 s5_08997_02497_04997_256 s5_11497_05497_03997_256
s5_15494_04494_02494_512 s5_16997_03497_03997_256"
SMOKE=s5_13497_01497_02497_256
CODE="seed_heading_confirmation.py neural_tracer_ct_context.py villa_seed_heading_rerun.py seed_heading_chain_status.py
make_tracer_presence.py neural_tracer_analysis.py afv_generator_analysis.py afv_to_labels.py neural_tracer_boundary.py
raw_tiff_region.py tolerance4_rescore.py"
mkdir -p "$W" || { echo "SC_ABORTED cannot create $W" >&2; exit 3; }
W=$(cd "$W" && pwd -P) || { echo "SC_ABORTED cannot resolve $W" >&2; exit 3; }
LOG=$W/chain.log
say() {
  echo "$*  $(date -Is)" | tee -a "$LOG" \
    || { echo "SC_ABORTED cannot append to $LOG" >&2; exit 3; }
}
command -v flock > /dev/null || { say "SC_ABORTED flock is required"; exit 3; }
if [ -L "$W/chain.lock" ] || { [ -e "$W/chain.lock" ] && [ ! -f "$W/chain.lock" ]; }; then
  echo "SC_ABORTED chain.lock must be a regular file, not a symlink" >&2; exit 3
fi
exec 9>>"$W/chain.lock" || { say "SC_ABORTED cannot open the chain lease"; exit 3; }
flock -n 9 || { echo "SC_ABORTED another launcher or worker holds $W/chain.lock" >&2; exit 3; }
if [ "$DRY_RUN" != 1 ]; then
# Only 1 means nothing is running: 0 is a running loop, and 2 means loop_control cannot tell.
"$PY" "$LOOPDIR/scripts/loop_control.py" status --repo "$LOOPDIR" > /dev/null
case $? in
  1) ;;
  0) say "SC_ABORTED the autoresearch loop is running"; exit 3 ;;
  *) say "SC_ABORTED loop_control.py status cannot tell whether the autoresearch loop is running"; exit 3 ;;
esac
for p in /proc/[0-9]*; do
  [ "$p" = "/proc/$$" ] && continue
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null \
    | grep -qE "tracers\.fibers\.tracing\.volume|neural_tracer_heading_arm|neural_tracer_refit_arm|bench_cli (trace|score|floors)|seed_heading_confirmation\.py presence|f1_noise_probe" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
fi

# Frozen once per study: a resume after the repository moves must not swap the code or the patch mid-study.
mkdir -p "$W/code" || { say "SC_ABORTED freeze"; exit 3; }
for f in $CODE; do
  if [ -e "$W/code/$f" ]; then
    cmp -s "$REPO/scripts/$f" "$W/code/$f" || { say "SC_ABORTED $f differs from the copy frozen in $W"; exit 3; }
  else
    cp "$REPO/scripts/$f" "$W/code/" || { say "SC_ABORTED freeze"; exit 3; }
  fi
done
PATCH="$REPO/repro/fibers/villa_volume_seed_heading.patch"
if [ -e "$W/patch" ]; then
  cmp -s "$PATCH" "$W/patch" || { say "SC_ABORTED the patch differs from the copy frozen in $W"; exit 3; }
else
  cp "$PATCH" "$W/patch" || { say "SC_ABORTED freeze"; exit 3; }
fi
STUDY="$W/code/seed_heading_confirmation.py"

# The two sources: villa's tree at VILLA_SHA, and the same with the patch, extracted once. GNU patch, not git apply:
# $W can sit inside another git repository, where git apply resolves paths from that repository's top.
[ "$(git -C "$VILLA_GIT" rev-parse "$VILLA_SHA^{commit}" 2>/dev/null)" = "$VILLA_SHA" ] \
  || { say "SC_ABORTED VILLA_GIT ($VILLA_GIT) does not hold $VILLA_SHA"; exit 3; }
VOL=vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py
for side in before after; do
  if [ ! -d "$W/src_$side" ]; then
    [ -e "$W/src_$side.tmp" ] && { say "SC_ABORTED $W/src_$side.tmp is left from an interrupted launch"; exit 3; }
    mkdir -p "$W/src_$side.tmp" || { say "SC_ABORTED prepare $side"; exit 3; }
    git -C "$VILLA_GIT" archive "$VILLA_SHA" vesuvius/src | tar -x -C "$W/src_$side.tmp" \
      || { say "SC_ABORTED extract $side"; exit 3; }
    if [ "$side" = after ]; then
      patch -d "$W/src_after.tmp" -p1 --batch --forward < "$W/patch" >> "$LOG" 2>&1 \
        || { say "SC_ABORTED the patch does not apply to $VILLA_SHA"; exit 3; }
    fi
    mv "$W/src_$side.tmp" "$W/src_$side" || { say "SC_ABORTED publish $side sources"; exit 3; }
  fi
done
# The skip is in before's volume.py and not in after's, whose new test exists; both take --no-fibers (villa #2316).
grep -q 'np.cos(np.radians(35))' "$W/src_before/$VOL" && ! grep -q 'np.cos(np.radians(35))' "$W/src_after/$VOL" \
  && [ -f "$W/src_after/vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_seed_heading.py" ] \
  && grep -q -- "'--no-fibers'" "$W/src_before/$VOL" && grep -q -- "'--no-fibers'" "$W/src_after/$VOL" \
  || { say "SC_ABORTED the extracted sources are not villa's and villa's with the patch"; exit 3; }
[ -d "$VC_SITE/vc_object_store" ] || { say "SC_ABORTED no vc_object_store in VC_SITE ($VC_SITE)"; exit 3; }
for side in before after; do
  got=$(cd "$W" && PYTHONPATH="$W/src_$side/vesuvius/src:$VC_SITE" HF_HUB_OFFLINE=1 "$TPY" -c \
    'import vesuvius.neural_tracing.tracers.fibers.tracing.volume as v; print(v.__file__)' 2>>"$LOG") \
    || { say "SC_ABORTED $side import check failed"; exit 3; }
  [ "$got" = "$W/src_$side/$VOL" ] || { say "SC_ABORTED $side imports volume.py from ${got:-nowhere}"; exit 3; }
done
trace_args() {  # side cube ct presence box out: ARGS, finding 97's command
  ARGS=(-m vesuvius.neural_tracing.tracers.fibers.tracing.volume
    --checkpoint "$CKPT" --ct "$3" --ct-level 0 --ct-grid-scale 1 --grid-scale 2
    --presence "$4" --box "$5" --base-um 7.91 --no-fibers --out "$6")
}
box() { local n=${1##*_}; echo "64,64,64,$((64 + n / 2)),$((64 + n / 2)),$((64 + n / 2))"; }
if [ "$DRY_RUN" = 1 ]; then
  trace_args before "$SMOKE" "$T/ct_context_run/ct/$SMOKE.zarr" "$T/ct_context_run/presence/${SMOKE}_presence.zarr/1" \
    "$(box "$SMOKE")" "$W/smoke/$SMOKE"
  echo "DRY_RUN smoke: ${ARGS[*]}"
  for side in before after; do
    for C in $CUBES; do
      trace_args "$side" "$C" "$W/ct/$C.zarr" "$W/presence/${C}_presence.zarr/1" "$(box "$C")" "$W/$side/$C"
      echo "DRY_RUN $side: PYTHONPATH=$W/src_$side/vesuvius/src:$VC_SITE HF_HUB_OFFLINE=1 $TPY ${ARGS[*]}"
    done
  done
  say "DRY_RUN_OK villa ${VILLA_SHA:0:9}"
  exit 0
fi
"$PY" -c 'import json, sys; p = json.load(open(sys.argv[1])); sys.exit(not (len(p) == 10 and all(r["core_equals_dataset004"] for r in p.values())))' \
  "$W/prepared.json" 2>/dev/null || { say "SC_ABORTED the padded CT is not prepared, or a core differs (run fetch first)"; exit 3; }
say "CHAIN_START repo $(git -C "$REPO" rev-parse --short HEAD) villa ${VILLA_SHA:0:9}"

# The presence: fiber_hz_vt on each cube's own image, on the GPU, as finding 91's presence was made.
if [ ! -f "$W/presence.json" ]; then
  ( cd "$REPO" && "$PY" "$STUDY" presence --work "$W" --device cuda ) >> "$W/presence.log" 2>&1 \
    || { say "SC_ABORTED presence (see $W/presence.log)"; exit 3; }
fi
"$PY" -c 'import json, sys; p = json.load(open(sys.argv[1])); sys.exit(not (len(p) == 10 and all(r["core_equals_level"] and r["inference_device"] == "cuda" for r in p.values())))' \
  "$W/presence.json" || { say "SC_ABORTED the presence is incomplete or was not made on the GPU"; exit 3; }

# The smoke: `before` with finding 97's inputs must reproduce finding 97's run point for point.
if [ ! -f "$W/smoke.json" ]; then
  rm -rf "$W/smoke/$SMOKE"
  mkdir -p "$W/smoke" || { say "SC_ABORTED prepare smoke"; exit 3; }
  say "SMOKE_START $SMOKE"
  trace_args before "$SMOKE" "$T/ct_context_run/ct/$SMOKE.zarr" "$T/ct_context_run/presence/${SMOKE}_presence.zarr/1" \
    "$(box "$SMOKE")" "$W/smoke/$SMOKE"
  ( cd "$W" && PYTHONPATH="$W/src_before/vesuvius/src:$VC_SITE" HF_HUB_OFFLINE=1 "$TPY" "${ARGS[@]}" ) \
    > "$W/smoke/$SMOKE.log" 2>&1 || { say "SC_ABORTED the smoke trace failed"; exit 3; }
  ( cd "$REPO" && "$PY" "$STUDY" smoke --work "$W" ) >> "$LOG" 2>&1
fi
"$PY" -c 'import json, sys; sys.exit(not json.load(open(sys.argv[1]))["identical"])' "$W/smoke.json" \
  || { say "SC_ABORTED SMOKE_FAILED: before does not reproduce finding 97's run"; exit 3; }

failed=0
for side in before after; do
  for C in $CUBES; do
    if ( cd "$REPO" && "$PY" "$STUDY" done --work "$W" --side "$side" --cube "$C" ); then
      say "SKIP_DONE $side $C"
      continue
    fi
    rm -rf "$W/$side/$C"
    mkdir -p "$W/$side" || { say "SC_ABORTED prepare $side output"; exit 3; }
    say "TRACE $side $C"
    trace_args "$side" "$C" "$W/ct/$C.zarr" "$W/presence/${C}_presence.zarr/1" "$(box "$C")" "$W/$side/$C"
    ( cd "$W" && PYTHONPATH="$W/src_$side/vesuvius/src:$VC_SITE" HF_HUB_OFFLINE=1 "$TPY" "${ARGS[@]}" ) > "$W/$side/$C.log" 2>&1
    rc=$?
    if [ "$rc" -eq 0 ]; then say "DONE $side $C"; else say "FAILED $side $C rc=$rc"; failed=$((failed + 1)); fi
  done
done
[ "$failed" -eq 0 ] || { say "CHAIN_FAILED $failed trace(s) failed"; exit 1; }
for side in before after; do
  for C in $CUBES; do
    ( cd "$REPO" && "$PY" "$STUDY" done --work "$W" --side "$side" --cube "$C" ) \
      || { say "CHAIN_FAILED $side $C has no closed outputs"; exit 1; }
  done
done
say "CHAIN_COMPLETE"
