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
