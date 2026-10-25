#!/usr/bin/env bash
# docs/VILLA_DRAFT_volume_seed_heading.md, "Before posting" step 3: the draft's numbers were measured at villa ccb431818,
# before villa #2165 rewrote the volume tracer's hot path ("exact-output checks"). This re-runs villa's own CLI at a
# later villa commit, with and without repro/fibers/villa_volume_seed_heading.patch, on the two held-out Scroll-5 cubes,
# with finding 97's inputs and command. `before` must reproduce finding 97's run and `after` finding 100's `keep` arm
# point for point; scripts/villa_seed_heading_rerun.py compares and records them (and scores any run that differs).
# villa's source comes from VILLA_GIT, a checkout holding VILLA_SHA (git archive: its working tree is not read); it
# runs in finding 97's tracer environment ($T/venv) with that source first on PYTHONPATH, which the chain checks.
# Refuses to start while the autoresearch loop or another GPU job runs. Nothing is fetched. Afterwards, CPU only:
#   (cd $REPO && nice -n 19 .venv/bin/python scripts/villa_seed_heading_rerun.py --work $W)
# Launch detached: setsid nohup bash <this> > $W.launch.log 2>&1 < /dev/null & disown
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
LOOPDIR="${LOOPDIR:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
TPY="$T/venv/bin/python"
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
VILLA_GIT="${VILLA_GIT:-}"
VILLA_SHA="${VILLA_SHA:-322cb0899ac9efe2588d5a3395dce6dc2dea3c89}"
W="${W:-$T/villa_rerun_${VILLA_SHA:0:9}}"
PATCH="$REPO/repro/fibers/villa_volume_seed_heading.patch"
CKPT="scrollprize/fiber_single_small@451182558cb3270cfc2ddf967acbd4f36b9b816b"
CUBES="s5_13497_01497_02497_256 s5_16997_03997_04497_256"
mkdir -p "$W"
LOG=$W/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }
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
    | grep -qE "tracers\.fibers\.tracing\.volume|neural_tracer_heading_arm|bench_cli (trace|score|floors)|f1_noise_probe" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done

# The two sources: villa's tree at VILLA_SHA, and the same with the patch, extracted once. The patch is frozen into $W
# on the first launch; a resume refuses if the repository's copy has changed. GNU patch, not git apply: $W can sit
# inside another git repository, where git apply resolves paths from that repository's top and skips the rest.
if [ -e "$W/patch" ]; then
  cmp -s "$PATCH" "$W/patch" || { say "SC_ABORTED the patch differs from the copy frozen in $W"; exit 3; }
else
  cp "$PATCH" "$W/patch" || { say "SC_ABORTED freeze"; exit 3; }
fi
[ -n "$VILLA_GIT" ] && [ "$(git -C "$VILLA_GIT" rev-parse "$VILLA_SHA^{commit}" 2>/dev/null)" = "$VILLA_SHA" ] \
  || { say "SC_ABORTED VILLA_GIT (${VILLA_GIT:-unset}) does not hold $VILLA_SHA"; exit 3; }
VOL=vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py
for side in before after; do
  if [ ! -d "$W/src_$side" ]; then
    [ -e "$W/src_$side.tmp" ] && { say "SC_ABORTED $W/src_$side.tmp is left from an interrupted launch"; exit 3; }
    mkdir -p "$W/src_$side.tmp"
    git -C "$VILLA_GIT" archive "$VILLA_SHA" vesuvius/src | tar -x -C "$W/src_$side.tmp" \
      || { say "SC_ABORTED extract $side"; exit 3; }
    if [ "$side" = after ]; then
      patch -d "$W/src_after.tmp" -p1 --batch --forward < "$W/patch" >> "$LOG" 2>&1 \
        || { say "SC_ABORTED the patch does not apply to $VILLA_SHA"; exit 3; }
    fi
    mv "$W/src_$side.tmp" "$W/src_$side"
  fi
done
# The skip is in before's volume.py and not in after's, whose new test exists.
grep -q 'np.cos(np.radians(35))' "$W/src_before/$VOL" && ! grep -q 'np.cos(np.radians(35))' "$W/src_after/$VOL" \
  && [ -f "$W/src_after/vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_seed_heading.py" ] \
  || { say "SC_ABORTED the extracted sources are not villa's and villa's with the patch"; exit 3; }
for side in before after; do
  got=$(cd "$W" && PYTHONPATH="$W/src_$side/vesuvius/src" HF_HUB_OFFLINE=1 "$TPY" -c \
    'import vesuvius.neural_tracing.tracers.fibers.tracing.volume as v; print(v.__file__)' 2>>"$LOG")
  [ "$got" = "$W/src_$side/$VOL" ] \
    || { say "SC_ABORTED $side imports volume.py from ${got:-nowhere}"; exit 3; }
done
say "CHAIN_START repo $(git -C "$REPO" rev-parse --short HEAD) villa ${VILLA_SHA:0:9}"

for side in before after; do
  for C in $CUBES; do
    out="$W/$side/$C"
    [ -f "$out/fibers.afv" ] && { say "SKIP_DONE $side $C"; continue; }
    mkdir -p "$W/$side"
    say "TRACE $side $C"
    ( cd "$W" && PYTHONPATH="$W/src_$side/vesuvius/src" HF_HUB_OFFLINE=1 \
        "$TPY" -m vesuvius.neural_tracing.tracers.fibers.tracing.volume \
        --checkpoint "$CKPT" --ct "$T/ct_context_run/ct/$C.zarr" --ct-level 0 --ct-grid-scale 1 --grid-scale 2 \
        --presence "$T/ct_context_run/presence/${C}_presence.zarr/1" --box 64,64,64,192,192,192 --base-um 7.91 \
        --afv-template "$G/run/$C.afv" --out "$out" ) > "$out.log" 2>&1
    rc=$?
    if [ "$rc" -eq 0 ] && [ -f "$out/fibers.afv" ]; then say "DONE $side $C"; else say "FAILED $side $C rc=$rc"; fi
  done
done
say "CHAIN_COMPLETE"
