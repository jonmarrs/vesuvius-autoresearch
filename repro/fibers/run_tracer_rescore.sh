#!/usr/bin/env bash
# docs/preregistration/2026-10-05_tracer_rescore.md -- run our fiber tracer at its published defaults on all 11
# ScrollGT cubes, saving each instance labelling, then score them (scripts/tracer_rescore_analysis.py, frozen into
# $W at start). A cube that fails is recorded and skipped, not fatal: the 512^3 cubes were never traced before.
# Resumable: a cube with saved instances is skipped.
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
W="${W:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/tracer_rescore}"
# Analysis script (frozen into $W) and its extra arguments. The defaults are finding 80's registered analysis.
ANALYSIS="${ANALYSIS:-tracer_rescore_analysis.py}"
ANALYSIS_ARGS="${ANALYSIS_ARGS:-}"
# Extra trace flags, logged per cube: Amendment 1 runs the 512^3 cubes with TRACE_EXTRA="--detect-block 128".
TRACE_EXTRA="${TRACE_EXTRA:-}"
CUBES="s1_00497_01497_03997_256 s1_00497_02497_02997_256 s1_00997_02497_02997_256 s1_08997_02997_02497_256
s1_10997_02997_02997_256 s5_03997_01497_03997_256 s5_07997_02997_05497_256 s5_14997_01497_01497_256
s5_06494_01994_03994_512 s5_06994_00994_04994_512 s5_07994_01994_05494_512"
mkdir -p "$W"
LOG=$W/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }
for p in /proc/[0-9]*; do
  [ "$p" = "/proc/$$" ] && continue
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -qE "bench_cli (trace|score|floors)|get_ink_metrics.py" && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
cp "$REPO/scripts/tracer_rescore_analysis.py" "$REPO/scripts/$ANALYSIS" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD)"
for C in $CUBES; do
  [ -f "$W/${C}_instances.npy" ] && { say "SKIP_DONE $C"; continue; }
  say "TRACE $C ${TRACE_EXTRA}"
  ( cd "$REPO" && "$PY" -m vesuvius_autoresearch.fibers.bench_cli trace --cube "$C" --device cuda \
      --save-instances "$W/${C}_instances.npy" --json-out "$W/${C}_trace.json" $TRACE_EXTRA ) > "$W/$C.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/${C}_instances.npy" ]; then say "DONE $C"; else say "FAILED $C rc=$rc"; fi
done
say "CHAIN_COMPLETE"
( cd "$REPO" && "$PY" "$W/$ANALYSIS" --work "$W" --out "$W/result.json" $ANALYSIS_ARGS ) > "$W/analysis.log" 2>&1
say "ANALYSIS rc=$?"
