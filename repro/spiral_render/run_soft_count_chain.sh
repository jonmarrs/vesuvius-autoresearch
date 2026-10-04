#!/usr/bin/env bash
# docs/preregistration/2026-10-04_soft_count.md -- re-score stored strips with villa's scorer, keeping the ensemble
# probability map, and record H (total_fg_pixels) and S (sum of probability) per arm. Outputs go ONLY to
# $WORK/<arm>/; each arm's published ink_metric/ is read, never written. Launch through run_snapshot.sh.
# Resumable: an arm with sums.json is skipped; a partial output is moved aside, not deleted.
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
WORK=$SO/softcount_study
TREE=$SO/gt_interp/scorer_tree/spiral-fitting
VENV=/home/jon/openclaw-workspace/Neo-VM/data/ink_scorer_venv/bin/python
DISK_FREE_GUARD_GB=100
# Order: pinned seeds, then the offset sweep (together the primary questions), then the current-tier replication.
ARMS="outer_baseline01 outer_seed02 outer_seed03 outer_seed04 outer_seed05 outer_seed06
outer_gap133 outer_gap133s2 outer_gap133s3 outer_gap133s4 outer_gap133s5 outer_gap133s6
flat_study_zero flat_study_probe flat_study_in flat_study_out offset_m2 offset_p1 offset_p2 offset_p3
outer_curbase_s4 outer_curbase_s5 outer_curbase_s6 outer_curbase_s7 outer_curbase_s8 outer_curbase_s9
outer_nosamecur_s1 outer_nosamecur_s2 outer_nosamecur_s3 outer_nosamecur_s4 outer_nosamecur_s5 outer_nosamecur_s6"
REUSE="outer_curbase_s1 outer_curbase_s2 outer_curbase_s3"   # 09-14 maps, same patched scorer
mkdir -p "$WORK"
LOG=$WORK/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }

busy() {
  for p in /proc/[0-9]*; do
    [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && return 0
    [ "$p" = "/proc/$$" ] && continue
    tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -q "get_ink_metrics.py" && return 0
  done
  return 1
}
busy && { say "SC_ABORTED a render or scorer is already running"; exit 3; }
grep -q INK_METRIC_KEEP_PROB "$TREE/get_ink_metrics.py" || { say "SC_ABORTED scorer tree lacks keep-prob"; exit 3; }
grep -q INK_METRIC_SERIAL_FOLDS "$TREE/get_ink_metrics.py" || { say "SC_ABORTED scorer tree lacks serial folds"; exit 3; }
[ -x "$VENV" ] || { say "SC_ABORTED no scorer venv"; exit 3; }
cp "$REPO/scripts/soft_count_sums.py" "$REPO/scripts/soft_count_study.py" "$WORK/" || { say "SC_ABORTED freeze"; exit 3; }
export INK_METRIC_KEEP_PROB=1 INK_METRIC_SERIAL_FOLDS=1
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD)"

for A in $REUSE; do
  [ -f "$WORK/$A/sums.json" ] && continue
  "$PY" "$WORK/soft_count_sums.py" "$SO/$A/ink_metric_prob" "$WORK/$A/sums.json" >> "$LOG" 2>&1 \
    || { say "SUMS_FAILED $A (reuse)"; exit 1; }
  say "REUSED $A"
done

for A in $ARMS; do
  O=$WORK/$A
  [ -f "$O/sums.json" ] && { say "SKIP_DONE $A"; continue; }
  [ -e "$O" ] && { mv "$O" "$O.partial.$(date +%s)"; say "MOVED_PARTIAL $A"; }
  FREE=$(df --output=avail -BG "$SO" | tail -1 | tr -dc 0-9)
  [ "$FREE" -ge "$DISK_FREE_GUARD_GB" ] || { say "DISK_GUARD ${FREE}GB free"; exit 4; }
  ls "$SO/$A/meshes/ink/"*.jpg > /dev/null 2>&1 || { say "NO_STRIPS $A"; exit 1; }
  say "SCORE $A"
  ( cd "$TREE" && "$VENV" -u get_ink_metrics.py "$SO/$A/meshes/ink" --output "$O" ) > "$WORK/$A.score.log" 2>&1
  rc=$?
  { [ "$rc" -eq 0 ] && [ -f "$O/metrics.json" ]; } || { say "SCORE_FAILED $A rc=$rc"; exit 1; }
  "$PY" "$WORK/soft_count_sums.py" "$O" "$O/sums.json" >> "$LOG" 2>&1 || { say "SUMS_FAILED $A"; exit 1; }
  say "DONE $A"
done

say "CHAIN_COMPLETE"
( cd "$REPO" && "$PY" "$WORK/soft_count_study.py" --study "$WORK" --out "$WORK/result.json" ) > "$WORK/analysis.log" 2>&1
say "ANALYSIS rc=$?"
