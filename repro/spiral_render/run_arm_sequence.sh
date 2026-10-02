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
# and verifies each requested winding.
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
# Resolve the villa checkout HERE, before anything snapshots the scripts. The
# renders run from a frozen copy under <work_root>/_driver_snapshot_*, where
# setup_workdir.sh's fallback ($0/../../villa) points nowhere. Without this every
# render fails at setup in the same second (2026-09-28, nosamecur_s4: 3 attempts,
# 0 renders). The other chain drivers already export VILLA; this one did not.
export VILLA="${VILLA:-$(cd "$HERE/../../villa" && pwd)}"
[ -d "$VILLA/.git" ] || [ -f "$VILLA/.git" ] || { echo "no villa checkout at $VILLA; set VILLA" >&2; exit 2; }

ROOT="${1:?usage: run_arm_sequence.sh <work_root> <first> <last> <tag> [tag...]}"
FIRST="${2:?}"
LAST="${3:?}"
shift 3
[ "$#" -gt 0 ] || { echo "no tags given" >&2; exit 2; }
[[ "$FIRST" =~ ^[0-9]+$ && "$LAST" =~ ^[0-9]+$ ]] && (( 10#$FIRST <= 10#$LAST )) \
  || { echo "windings must be ordered non-negative integers" >&2; exit 2; }
FIT_MESH_WAIT_SECONDS="${FIT_MESH_WAIT_SECONDS:-3600}"
[[ "$FIT_MESH_WAIT_SECONDS" =~ ^[0-9]+$ ]] \
  || { echo "FIT_MESH_WAIT_SECONDS must be a non-negative integer" >&2; exit 2; }
FAILED=0

WINDINGS=()
for ((w = 10#$FIRST; w <= 10#$LAST; w++)); do WINDINGS+=("$(printf '%03d' "$w")"); done
EXPECT=${#WINDINGS[@]}

meshes_for() {  # tag -> mesh dir, empty if absent
  local t="$1"
  local candidates=()
  shopt -s nullglob
  candidates=("$ROOT"/*patch_"$t"/meshes/fitted_"$t")
  shopt -u nullglob
  [ "${#candidates[@]}" -le 1 ] \
    || { echo "[fail] ambiguous fitted mesh directories for $t" >&2; return 1; }
  if [ "${#candidates[@]}" -eq 1 ]; then printf '%s\n' "${candidates[0]}"; fi
}

meshes_ready() {
  python3 "$HERE/artifacts.py" meshes "$1" "$FIRST" "$LAST" 2>/dev/null
}

for TAG in "$@"; do
  [[ "$TAG" =~ ^[a-zA-Z0-9_-]+$ ]] \
    || { echo "[fail] invalid arm tag: $TAG" >&2; FAILED=1; continue; }
  echo "################ $TAG $(date -Is) ################"

  if python3 "$HERE/artifacts.py" arm "$ROOT/outer_$TAG" "$FIRST" "$LAST" 2>/dev/null; then
    echo "[skip] $TAG already scored"; continue
  fi

  MESHES=$(meshes_for "$TAG") || { FAILED=1; continue; }
  if ! meshes_ready "$MESHES"; then
    [ -x "$ROOT/fit_$TAG.sh" ] || { echo "[fail] no $ROOT/fit_$TAG.sh"; FAILED=1; continue; }
    echo "[fit] $TAG $(date -Is)"
    "$ROOT/fit_$TAG.sh" > "$ROOT/fit_$TAG.log" 2>&1
    rc=$?
    echo "[fit] $TAG rc=$rc $(date -Is)"
    [ "$rc" -eq 0 ] || { echo "[fail] fit $TAG"; FAILED=1; continue; }
    # Wait on the MESHES, not on the satisfaction json. See the note above.
    DEADLINE=$(( $(date +%s) + 10#$FIT_MESH_WAIT_SECONDS ))
    while true; do
      MESHES=$(meshes_for "$TAG") || { FAILED=1; break; }
      meshes_ready "$MESHES" && break
      [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] $TAG meshes never appeared"; break; }
      sleep 30
    done
  else
    echo "[skip] $TAG already fitted"
  fi

  meshes_ready "$MESHES" || { echo "[fail] $TAG is missing requested meshes, skipping"; FAILED=1; continue; }
  echo "[check] $TAG has all $EXPECT requested winding meshes"

  echo "[render+score] $TAG $(date -Is)"
  RETRY_WAIT_FIRST=0 "$HERE/run_with_retry.sh" 3 "$ROOT" "$FIRST" "$LAST" "$TAG=$MESHES" \
    >> "$ROOT/sequence_$TAG.log" 2>&1
  rc=$?
  echo "[render+score] $TAG rc=$rc $(date -Is)"

  [ "$rc" -eq 0 ] && python3 "$HERE/artifacts.py" arm "$ROOT/outer_$TAG" "$FIRST" "$LAST" \
    && echo "[ok] $TAG scored" \
    || { echo "[fail] $TAG NOT scored after retries"; FAILED=1; }
done
echo "################ SEQUENCE DONE $(date -Is) rc=$FAILED ################"
exit "$FAILED"
