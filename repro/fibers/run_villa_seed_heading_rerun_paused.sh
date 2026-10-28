#!/usr/bin/env bash
# Pause the autoresearch loop around repro/fibers/run_villa_seed_heading_rerun.sh (a GPU job the owner approves): wait
# for a loop cycle to start that is not one of the unchanged-control registration's arms (#264), so no arm cycle is
# lost; stop the loop; run the chain from REPO (a checkout of main, not the loop's); start the loop again, whatever
# the chain did. Used for the 2026-10-28 re-run at villa 39a8cf3a (reports/evidence/*_39a8cf3a_wrapper.txt).
#   REPO=<checkout> WRAPLOG=<file> setsid bash <this> > /dev/null 2>&1 < /dev/null & disown
set -uo pipefail
L=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
REPO="${REPO:?a checkout of main holding #281}"
WRAPLOG="${WRAPLOG:?the wrapper log}"
OUT=$L/autoresearch.out
PAT='^Running .*-minute training for '
ts() { date '+%F %T'; }
say() { echo "$(ts) $*" >> "$WRAPLOG"; }
[ -f "$REPO/repro/fibers/run_villa_seed_heading_rerun.sh" ] && grep -q -- "--no-fibers" "$REPO/repro/fibers/run_villa_seed_heading_rerun.sh" \
  || { say "ABORT $REPO has no object-store chain"; exit 3; }
n=$(grep -c "$PAT" "$OUT")
say "WAIT for a cycle start after $n that is not control_unchanged or aug_mode_albumentations"
while :; do
  sleep 5
  m=$(grep -c "$PAT" "$OUT")
  [ "$m" -gt "$n" ] || continue
  n=$m
  line=$(grep "$PAT" "$OUT" | tail -1)
  case "$line" in
    *" for control_unchanged..."|*" for aug_mode_albumentations...") say "an arm started, waiting: $line"; continue ;;
  esac
  say "next cycle started: $line"
  break
done
bash "$L/stop.sh" >> "$WRAPLOG" 2>&1
say "stop.sh rc=$?"
python3 "$L/scripts/loop_control.py" status --repo "$L" > /dev/null 2>&1
echo "status rc=$?" >> "$WRAPLOG"
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader >> "$WRAPLOG" 2>&1
VILLA_GIT="${VILLA_GIT:-/home/jon/openclaw-workspace/Neo-VM/projects/villa-current-39a8cf3a}" REPO="$REPO" \
  bash "$REPO/repro/fibers/run_villa_seed_heading_rerun.sh" >> "$WRAPLOG" 2>&1 < /dev/null
say "chain rc=$?"
bash "$L/start.sh" >> "$WRAPLOG" 2>&1
say "start.sh rc=$?"
say "WRAPPER_DONE"
