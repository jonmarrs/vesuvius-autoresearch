#!/usr/bin/env bash
# Fit, render and score a list of arms end to end, one at a time.
#
# The other drivers here start from meshes that already exist. This one starts
# from nothing: it runs the fit too, which is what a power extension needs (five
# new fits, five renders, five scorings, about 24 hours).
#
# Strictly sequential, and not negotiably: a render peaks near 26GB on a 32GB box
# and a fit competes with it for both GPU and RAM.
#
# THE FIT/MESH RACE, which cost an arm before it was understood: fit_spiral.py
# writes satisfaction_metrics_fitted.json about a minute BEFORE it writes its
# meshes. A driver keyed to that json wakes early, finds no meshes and silently
# drops the arm. This waits on the MESHES -- the artifact it is about to consume --
# and counts them.
#
# Resumable at every stage: an arm already scored is skipped, an arm already
# fitted is not refitted. Renders go through run_with_retry.sh because one render
# in six is OOM-killed here.
#
# Usage:
#   run_arm_sequence.sh <work_root> <first_winding> <last_winding> <tag> [tag...]
#
# Expects, for each <tag>:
#   <work_root>/fit_<tag>.sh                         the fit script
#   <work_root>/*patch_<tag>/meshes/fitted_<tag>/    where it puts its meshes
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

ROOT="${1:?usage: run_arm_sequence.sh <work_root> <first> <last> <tag> [tag...]}"
FIRST="${2:?}"
LAST="${3:?}"
shift 3
[ "$#" -gt 0 ] || { echo "no tags given" >&2; exit 2; }

WINDINGS=()
for ((w = 10#$FIRST; w <= 10#$LAST; w++)); do WINDINGS+=("$(printf '%03d' "$w")"); done
EXPECT=${#WINDINGS[@]}

meshes_for() {  # tag -> mesh dir, empty if absent
  local t="$1" d
  d=$(ls -d "$ROOT"/*patch_"$t" 2>/dev/null | head -1) || return 0
  [ -n "$d" ] && ls -d "$d/meshes/fitted_$t" 2>/dev/null || true
}

count_meshes() {
  [ -n "$1" ] || { echo 0; return; }
  find "$1" -maxdepth 1 -name "w${WINDINGS[0]:0:1}*_spliced_*" 2>/dev/null | wc -l
}

for TAG in "$@"; do
  echo "################ $TAG $(date -Is) ################"

  if [ -f "$ROOT/outer_$TAG/ink_metric/metrics.json" ]; then
    echo "[skip] $TAG already scored"; continue
  fi

  MESHES=$(meshes_for "$TAG")
  if [ "$(count_meshes "$MESHES")" -lt "$EXPECT" ]; then
    [ -x "$ROOT/fit_$TAG.sh" ] || { echo "[fail] no $ROOT/fit_$TAG.sh"; continue; }
    echo "[fit] $TAG $(date -Is)"
    "$ROOT/fit_$TAG.sh" > "$ROOT/fit_$TAG.log" 2>&1
    echo "[fit] $TAG rc=$? $(date -Is)"
    # Wait on the MESHES, not on the satisfaction json. See the note above.
    DEADLINE=$(( $(date +%s) + 3600 ))
    until [ "$(count_meshes "$(meshes_for "$TAG")")" -ge "$EXPECT" ]; do
      [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] $TAG meshes never appeared"; break; }
      sleep 30
    done
    MESHES=$(meshes_for "$TAG")
  else
    echo "[skip] $TAG already fitted"
  fi

  n=$(count_meshes "$MESHES")
  [ "$n" -ge "$EXPECT" ] || { echo "[fail] $TAG has $n/$EXPECT meshes, skipping"; continue; }
  echo "[check] $TAG meshes $n/$EXPECT"

  echo "[render+score] $TAG $(date -Is)"
  RETRY_WAIT_FIRST=0 "$HERE/run_with_retry.sh" 3 "$ROOT" "$FIRST" "$LAST" "$TAG=$MESHES" \
    >> "$ROOT/sequence_$TAG.log" 2>&1
  echo "[render+score] $TAG rc=$? $(date -Is)"

  [ -f "$ROOT/outer_$TAG/ink_metric/metrics.json" ] \
    && echo "[ok] $TAG scored" \
    || echo "[fail] $TAG NOT scored after retries"
done
echo "################ SEQUENCE DONE $(date -Is) ################"
