#!/usr/bin/env bash
# When all three arms of triplet C are scored, run the REGISTERED analysis.
#
# docs/preregistration/2026-09-14_consensus_retest_calibrated.md, decided by
# scripts/analyse_consensus_retest.py, which was committed before triplet C existed
# and refuses a partial sample.
#
# Running this unattended is deliberate and does not weaken the registration -- it
# strengthens it. The decision rule, the validity gate and the retirement of the
# A-vs-B comparison are all in committed code; nobody is in the loop between seeing
# a number and deciding what it means.
#
# WAITS ON THE ARTIFACT IT WILL CONSUME, not on a process name and not on a
# completion message. fit_spiral.py once wrote its "done" json a minute before its
# meshes, and a driver keyed to that woke early and dropped an arm from a
# seven-arm study. Here the artifacts ARE the inputs: three ink_metric/metrics.json.
#
# It also waits for the box to be clear. The analysis loads nine arms; doing that
# beside a render drove MemAvailable to 0G on 2026-09-14.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
ROOT="${ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out}"
DEADLINE_H="${DEADLINE_H:-36}"
POLL_S="${POLL_S:-300}"
ARMS=(curbase_s7 curbase_s8 curbase_s9)

log() { echo "[analysis] $(date -Is) $*"; }
scored() { for t in "${ARMS[@]}"; do [ -f "$ROOT/outer_$t/ink_metric/metrics.json" ] || return 1; done; }

log "waiting for all of ${ARMS[*]} to be scored (deadline ${DEADLINE_H}h)"
deadline=$(( $(date +%s) + DEADLINE_H * 3600 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if scored && "$REPO/.venv/bin/python" "$REPO/scripts/guard_heavy_analysis.py" --fail-if-any >/dev/null 2>&1; then
    log "all three scored and the box is clear"
    break
  fi
  sleep "$POLL_S"
done
if ! scored; then
  log "DEADLINE reached without all three arms scored. Analysis NOT run; a partial"
  log "sample is refused, not reported. Missing:"
  for t in "${ARMS[@]}"; do
    [ -f "$ROOT/outer_$t/ink_metric/metrics.json" ] || log "  $t"
  done
  exit 1
fi

log "registered control: strip non-blank fraction per arm (expect 0.40-0.55)"
dirs=(); for t in "${ARMS[@]}"; do dirs+=("$ROOT/outer_$t"); done
"$REPO/.venv/bin/python" "$REPO/scripts/check_strip_nonblank.py" "${dirs[@]}" 2>&1 | sed 's/^/  /'

log "running the registered analysis"
"$REPO/.venv/bin/python" "$REPO/scripts/analyse_consensus_retest.py" \
  --json "$REPO/reports/consensus_retest_verdict.json" 2>&1 | sed 's/^/  /'
log "rc=$? -- verdict json at reports/consensus_retest_verdict.json"
