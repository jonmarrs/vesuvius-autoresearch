#!/usr/bin/env bash
# Wait for the running chain to finish, then render whatever of triplet C is missing.
#
# curbase_s7's render was OOM-killed three times on 2026-09-14 and the chain moved
# on, leaving it unscored. Its FIT is intact, so it needs a re-render only. s8 is
# scored; s9 is rendering. Rather than leave the box idle for hours between s9
# finishing and someone noticing, this waits and then completes the triplet.
#
# Safe to run against all three arms because run_arm_sequence.sh is idempotent:
# "[skip] TAG already scored" for s8 (and s9, once it lands) and "[skip] TAG already
# fitted" for s7, whose meshes survive. So this renders exactly what is missing.
#
# WAITING ON A CONDITION, NOT A PROCESS NAME. `pgrep -f <script>` matches every
# command line that merely contains the string -- the shell that wrote the script, a
# monitor grepping for it, the pgrep itself. Four variants of that bug have bitten
# this project. guard_heavy_analysis.py --fail-if-any keys on argv[0] and on the
# containerised renderer, and covers BOTH villa checkouts (fits run from
# villa-spiral-current, renders from villa-spiral).
#
# The deadline is sized for "this will NEVER finish", not "slower than I expected":
# s8 took 3h14m while thrashing, so 24h catches a genuinely wedged job without
# throwing away a study that is merely slow.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
ROOT="${ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out}"
DEADLINE_H="${DEADLINE_H:-24}"
POLL_S="${POLL_S:-300}"
export VILLA="${VILLA:-$REPO/villa}"
export VILLA_REF="${VILLA_REF:-be09a8503}"

log() { echo "[complete-c] $(date -Is) $*"; }

log "waiting for the running chain to finish (deadline ${DEADLINE_H}h, poll ${POLL_S}s)"
deadline=$(( $(date +%s) + DEADLINE_H * 3600 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if "$REPO/.venv/bin/python" "$REPO/scripts/guard_heavy_analysis.py" --fail-if-any >/dev/null 2>&1; then
    log "no villa job in flight; proceeding"
    break
  fi
  sleep "$POLL_S"
done
if [ "$(date +%s)" -ge "$deadline" ]; then
  log "DEADLINE reached with a job still in flight; NOT starting. Investigate."
  exit 1
fi

for t in curbase_s7 curbase_s8 curbase_s9; do
  f="$ROOT/outer_$t/ink_metric/metrics.json"
  log "$t scored: $([ -f "$f" ] && echo yes || echo NO)"
done

log "running recover_arm.sh for the triplet (already-scored arms are skipped)"
"$HERE/recover_arm.sh" "$ROOT" 120 129 curbase_s7 curbase_s8 curbase_s9
rc=$?
log "recover_arm.sh rc=$rc"
for t in curbase_s7 curbase_s8 curbase_s9; do
  f="$ROOT/outer_$t/ink_metric/metrics.json"
  log "final $t scored: $([ -f "$f" ] && echo yes || echo NO)"
done
log "done"
