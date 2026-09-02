#!/usr/bin/env bash
# Render AND score a winding range for several fits, one fit at a time.
#
# This is the driver behind the outer-winding arms:
#   docs/preregistration/2026-09-01_outer_winding_noise_floor.md
#   reports/gap_fix_outer_windings_still_not_established.md
#
# Sequential, and not negotiably so. vc_render_tifxyz peaks near 26GB on a
# ten-winding OUTER strip; two at once swaps a 32GB box into uselessness, and the
# scorer needs ~19GB of its own on top (see README section 7).
#
# Resumable: a fit whose ink_metric/metrics.json already exists is skipped, so an
# interrupted run picks up where it stopped rather than re-rendering two hours.
#
# If you chain this behind something else, WAIT ON A FILE, not on a process name.
# `pgrep -f <script>.sh` matches every command line that merely contains that
# string: the shell whose heredoc wrote the script, a monitor whose grep pattern
# mentions it, even the `pgrep` invocation itself. Two failures came from this in
# one session -- a driver that waited two hours for its own reflection, and a
# `pkill -f` that killed the shell issuing it. `until compgen -G <the artifact the
# job actually produces>` cannot self-match; give it a deadline and fail loudly.
#
# And wait on the LAST thing the job writes, or better, on the artifact you
# actually need. fit_spiral.py writes satisfaction_metrics_fitted.json about a
# minute BEFORE it writes its meshes, so a driver keyed to that json woke early,
# found no meshes and dropped an arm from a seven-arm study. The completion signal
# you can see is not always the completion. Check for the inputs you are about to
# consume -- here, the ten w12?_spliced_* directories -- and say how many you
# found.
#
# Size a watchdog deadline for "this will NEVER finish", not for "this is slower
# than I expected". 24h costs nothing and still catches a genuinely wedged job,
# whereas a deadline sized to the optimistic estimate can fail a chain of waiters
# while the study is nearly done, throwing away hours of good rendering to a timer
# rather than to a fault.
#
# DO NOT panic at the in-tool ETA, and do not read cumulative elapsed as per-band
# cost. These renders are FRONT-LOADED: the early bands are slow while the box
# builds swap pressure, and the late ones are quick. Two finished arms, cumulative
# elapsed:
#
#   band:        1       3       6      10      20      30     total
#   gap133     0m26s   2m33s  39m41s  75m12s 113m58s 118m32s  2h02m
#   seed03     0m27s   7m45s  45m49s  83m39s 111m33s 116m34s  2h00m
#
# Bands 20->30 cost about 5 minutes between them; bands 3->6 cost over half an
# hour. The progress line's ETA is a linear extrapolation from the slow part, so
# at band 6 it reads three to four hours for a job that finishes in two. To judge
# whether a render is actually in trouble, compare its band-6 elapsed against the
# table above, not against the ETA it prints.
#
# A /proc liveness sample is BIMODAL and one reading proves nothing. The same
# healthy render, sampled an hour apart:
#
#   1559 CPU ticks/20s with  1,436 major faults   <- compute phase
#    184 CPU ticks/20s with 31,435 major faults   <- fault-bound phase
#
# Neither means wedged; it alternates. vmstat over the second window still showed
# the box 78% idle with 0% iowait. If you want a liveness signal, take several
# samples over minutes, or just watch the band counter advance. (Fields: 14+15 of
# /proc/<pid>/stat for CPU ticks, field 10 for major faults.)
#
# Usage:
#   run_outer_arms.sh <out_root> <first_winding> <last_winding> <tag>=<fitted_meshes_dir> ...
#
# Example, the three honest seeds on the outer decade:
#   run_outer_arms.sh /path/spiral_out 120 129 \
#     seed02=/path/spiral_out/<fit_seed02>/meshes/fitted_seed02 \
#     seed03=/path/spiral_out/<fit_seed03>/meshes/fitted_seed03
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

ROOT="${1:?usage: run_outer_arms.sh <out_root> <first_winding> <last_winding> tag=meshes_dir ...}"
FIRST="${2:?first winding, e.g. 120}"
LAST="${3:?last winding, e.g. 129}"
shift 3
[ "$#" -gt 0 ] || { echo "no arms given" >&2; exit 2; }

WINDINGS=()
for ((w = 10#$FIRST; w <= 10#$LAST; w++)); do WINDINGS+=("$(printf '%03d' "$w")"); done
EXPECT=${#WINDINGS[@]}

for SPEC in "$@"; do
  TAG="${SPEC%%=*}"
  MESHES="${SPEC#*=}"
  W="$ROOT/outer_$TAG"
  echo "=================== ARM $TAG $(date -Is) ==================="

  if [ -f "$W/ink_metric/metrics.json" ]; then
    echo "[skip] $TAG already scored"
    continue
  fi
  if [ ! -d "$MESHES" ]; then
    echo "[fail] $TAG: no such meshes dir: $MESHES"
    continue
  fi
  if [ ! -d "$W/meshes" ]; then
    "$HERE/setup_workdir.sh" "$W" "$MESHES" "${WINDINGS[@]}" \
      || { echo "[fail] setup $TAG"; continue; }
  fi

  # Guard the count: setup_workdir globs, and a silently short copy would be
  # scored as though it were the full range.
  n=$(find "$W/meshes" -maxdepth 1 -name 'w*_spliced_*' | wc -l)
  echo "[check] $TAG has $n spliced meshes (expect $EXPECT)"
  [ "$n" -eq "$EXPECT" ] || { echo "[fail] wrong mesh count for $TAG"; continue; }

  echo "[render] $TAG $(date -Is)"
  "$HERE/run_render.sh" "$W" > "$ROOT/outer_${TAG}_render.log" 2>&1
  rc=$?   # captured on its own line; a $(...) in the echo would clobber $? first
  echo "[render] $TAG rc=$rc $(date -Is)"
  ls "$W"/meshes/ink/*.jpg >/dev/null 2>&1 \
    || { echo "[fail] no strips for $TAG"; continue; }

  echo "[score] $TAG $(date -Is)"
  "$HERE/score_arms.sh" "$W" >> "$ROOT/outer_${TAG}_render.log" 2>&1
  rc=$?
  echo "[score] $TAG rc=$rc $(date -Is)"
  [ -f "$W/ink_metric/metrics.json" ] \
    || echo "[fail] $TAG produced no metrics.json; re-score it before analysing"
done
echo "=================== ARMS DONE $(date -Is) ==================="
