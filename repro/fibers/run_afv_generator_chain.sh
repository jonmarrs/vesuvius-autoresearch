#!/usr/bin/env bash
# docs/preregistration/2026-10-11_afv_generator_entrant.md -- run villa PR #1934's vesuvius.afv_spline_generator at its
# defaults on the 11 ScrollGT fiber targets and the 10 held-out cubes, then score the .afv files
# (scripts/afv_generator_analysis.py, frozen into $W at start). A cube that fails is recorded and skipped.
# Resumable: a cube with a .afv is skipped. Launch detached: setsid nohup bash <this> > $W/launch.log 2>&1 &
set -uo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
PY="$REPO/.venv/bin/python"
G="${G:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen}"
GPY="$G/venv/bin/python"
W="${W:-$G/run}"
HELDOUT="${HELDOUT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_heldout}"
CUBES="s1_00497_01497_03997_256 s1_00497_02497_02997_256 s1_00997_02497_02997_256 s1_08997_02997_02497_256
s1_10997_02997_02997_256 s5_03997_01497_03997_256 s5_07997_02997_05497_256 s5_14997_01497_01497_256
s5_06494_01994_03994_512 s5_06994_00994_04994_512 s5_07994_01994_05494_512
s5_13497_01497_02497_256 s5_16997_03997_04497_256
s3_00994_00494_01994_512 s3_00994_01994_00494_512 s3_00994_02494_01494_512 s3_01994_01494_00994_512
s3_01994_01994_01494_512 s3_02994_02494_01994_512 s3_03494_01494_00494_512 s3_04494_00994_01494_512"
mkdir -p "$W"
LOG=$W/chain.log
say() { echo "$*  $(date -Is)" | tee -a "$LOG"; }
for p in /proc/[0-9]*; do
  [ "$p" = "/proc/$$" ] && continue
  tr '\0' ' ' < "$p/cmdline" 2>/dev/null | grep -qE "bench_cli (trace|score|floors)|get_ink_metrics.py|afv_spline_generator" \
    && { say "SC_ABORTED another GPU job is running"; exit 3; }
done
cp "$REPO/scripts/afv_generator_analysis.py" "$REPO/scripts/afv_to_labels.py" "$W/" || { say "SC_ABORTED freeze"; exit 3; }
say "CHAIN_START $(git -C "$REPO" rev-parse --short HEAD) generator $(git -C "$G/pr1934" rev-parse --short HEAD)"
for C in $CUBES; do
  [ -f "$W/$C.afv" ] && { say "SKIP_DONE $C"; continue; }
  N=${C##*_}
  say "GENERATE $C"
  # Offline: the pinned model revision is already in the Hugging Face cache and cannot move mid-run.
  ( cd "$W" && HF_HUB_OFFLINE=1 "$GPY" -m vesuvius.afv_spline_generator --volume "$G/zarr/$C.zarr" \
      --origin 0 0 0 --size "$N" "$N" "$N" --coordinate-space "scrollgt/$C" --voxel-size 7.91 --device cuda \
      --output "$W/$C.afv" ) > "$W/$C.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$W/$C.afv" ]; then say "DONE $C"; else say "FAILED $C rc=$rc"; fi
done
say "CHAIN_COMPLETE"
( cd "$REPO" && "$PY" "$W/afv_generator_analysis.py" --work "$W" --heldout-data "$HELDOUT/data" \
    --heldout-result "$HELDOUT/run/result.json" --out "$W/result.json" ) > "$W/analysis.log" 2>&1
say "ANALYSIS rc=$?"
