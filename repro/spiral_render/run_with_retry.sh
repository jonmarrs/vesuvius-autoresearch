#!/usr/bin/env bash
# Supervise an outer-arm render, relaunching it if it is OOM-killed.
#
# Outer renders sit within about 1GB of this box's limit: one of six was
# SIGKILLed at 26.9GB, losing ~2h because nothing is checkpointed. Retrying is
# the accepted answer here (the alternative, freeing ~1.5GB of desktop memory,
# is not always available), so this does the retrying without needing a human to
# notice.
#
# Safe to retry because run_outer_arms.sh is idempotent per arm: it SKIPS any arm
# that already has ink_metric/metrics.json, and it refuses to render an arm whose
# mesh count is wrong. A retry therefore either redoes exactly the failed work or
# does nothing.
#
# Each attempt runs from its OWN frozen snapshot via run_snapshot.sh, so editing
# the repo between attempts cannot corrupt an in-flight one.
#
# Usage:
#   run_with_retry.sh <attempts> <snapshot_root> <first> <last> <tag>=<meshes> ...
#
# Env:
#   RETRY_WAIT_FIRST=1   wait for an already-running render of these arms to
#                        finish before doing anything (default 1)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

ATTEMPTS="${1:?usage: run_with_retry.sh <attempts> <snapshot_root> <first> <last> tag=meshes ...}"
ROOT="${2:?}"
FIRST="${3:?}"
LAST="${4:?}"
shift 4
[ "$#" -gt 0 ] || { echo "no arms given" >&2; exit 2; }

TAGS=()
for spec in "$@"; do TAGS+=("${spec%%=*}"); done

scored() {   # every requested arm already has metrics
  for t in "${TAGS[@]}"; do
    [ -f "$ROOT/outer_$t/ink_metric/metrics.json" ] || return 1
  done
  return 0
}

running() {  # a render for one of these arms is alive
  for t in "${TAGS[@]}"; do
    pgrep -f "render_ink.py .*outer_$t/meshes" >/dev/null 2>&1 && return 0
  done
  return 1
}

if [ "${RETRY_WAIT_FIRST:-1}" = "1" ] && running; then
  echo "[retry] a render for these arms is already running; waiting for it $(date -Is)"
  while running; do sleep 60; done
  echo "[retry] it finished $(date -Is)"
fi

for i in $(seq 1 "$ATTEMPTS"); do
  if scored; then
    echo "[retry] all arms scored, nothing to do $(date -Is)"
    exit 0
  fi
  echo "=========== attempt $i of $ATTEMPTS $(date -Is) ==========="
  "$HERE/run_snapshot.sh" "$ROOT" run_outer_arms.sh "$ROOT" "$FIRST" "$LAST" "$@"
  rc=$?
  echo "[retry] attempt $i finished rc=$rc $(date -Is)"
  if scored; then
    echo "[retry] SUCCESS after $i attempt(s) $(date -Is)"
    exit 0
  fi
  echo "[retry] arms still unscored after attempt $i"
done

echo "[retry] GIVING UP after $ATTEMPTS attempts $(date -Is)"
echo "[retry] this is not a transient failure any more; read the render log before rerunning"
exit 1
