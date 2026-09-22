#!/usr/bin/env bash
# Engineering check, queued behind the offset sweep: does --cache-gb 8 stop the render thrashing
# WITHOUT changing a single output byte?
#
# Why: mid-chain the render holds ~27 GB on a 31 GB box and faults its own chunk cache back from
# swap (2.79M major faults, ~32 GB of block reads vs ~0.3 GB of syscall/HTTP reads in 70 min).
# The remote path keeps chunks ONLY in an in-memory cache sized by --cache-gb (default 16); the
# --volume dir just records the URL, so nothing persists between renders
# (villa 5479453a vc_render_tifxyz.cpp ~L1344).
#
# The test is zero-tolerance because the renderer is bit-deterministic given a fixed surface:
# radial_work_rad0 and flat_study_probe rendered byte-identical strips (6 jpg + 5 tif) and their
# scores still differed by 24 px, so that floor is the scorer's alone. So: re-render
# flat_study_zero's surface with --cache-gb 8 and cmp every strip. Identical => the setting is not
# an instrument change and future studies may adopt it. Any byte different => it is, and they may not.
# Scoring is skipped: byte-identity is the stronger test.
#
# Baseline render wall time, flatten reused, same canvas: zero 1h44m, in 1h43m, out 1h52m.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
SWEEP_PID="${SWEEP_PID:?set SWEEP_PID to the pid of run_offset_sweep_after_pooled.sh}"
REF=$SO/flat_study_zero
W=$SO/cachetest_g8
GB=8
OUTJSON=$REPO/reports/cache_gb_check.json
say() { echo "$*  $(date -Is)"; }

say "CACHE_CHECK waiting for offset sweep pid $SWEEP_PID"
while [ -d /proc/$SWEEP_PID ] && tr '\0' ' ' < /proc/$SWEEP_PID/cmdline 2>/dev/null | grep -q run_offset_sweep; do
  sleep 60
done
grep -q '^OFFSET_SWEEP_DONE' "$SO/offset_sweep.log" || {
  say "CACHE_CHECK_ABORTED offset sweep did not end with OFFSET_SWEEP_DONE -- the box may be needed for a re-run"; exit 3; }
sleep 30
[ -e "$W" ] && { say "CACHE_CHECK_ABORTED $W exists"; exit 5; }

# ---- stage: ZERO's work dir, outputs stripped, wrapper given --cache-gb -------------------------
cp -a "$REF" "$W"
rm -rf "$W/meshes/ink" "$W/ink_metric" "$W/meshes/ink_metric" "$W/meshes/concat/w120-129_flat/ink"
rm -f "$W"/meshes/concat/w120-129_flat/*.jpg
for f in x.tif y.tif z.tif meta.json; do
  cmp -s "$W/meshes/concat/w120-129_flat/$f" "$REF/meshes/concat/w120-129_flat/$f" \
    || { say "CACHE_CHECK_ABORTED staged $f differs from reference"; exit 1; }
done
sed -i "s|--scale-segmentation 4 \"\$@\"|--scale-segmentation 4 --cache-gb $GB \"\$@\"|" "$W/bin/vc_render_tifxyz"
grep -q -- "--cache-gb $GB" "$W/bin/vc_render_tifxyz" || { say "CACHE_CHECK_ABORTED wrapper edit did not apply"; exit 1; }

# ---- render, sampling the sampler's memory and faults ------------------------------------------
export RENDER_REUSE_FLATTEN=1
unset FLATTEN_DETERMINISTIC
SWPIN0=$(awk '/^pswpin/ {print $2}' /proc/vmstat)
T0=$(date +%s)
cd "$REPO/repro/spiral_render"
VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python \
  ./run_render.sh "$W" > "$SO/cachetest_g8.render.log" 2>&1 &
RP=$!
HWM=0; MAJ=0; SAW_FLAG=0
while kill -0 $RP 2>/dev/null; do
  for p in $(pgrep -x vc_render_tifxy); do
    tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q -- "--segmentation $W/" || continue
    tr '\0' ' ' < /proc/$p/cmdline | grep -q -- "--cache-gb $GB" && SAW_FLAG=1
    h=$(awk '/VmHWM/ {print $2}' /proc/$p/status 2>/dev/null); [ -n "$h" ] && [ "$h" -gt "$HWM" ] && HWM=$h
    m=$(awk '{print $12}' /proc/$p/stat 2>/dev/null); [ -n "$m" ] && [ "$m" -gt "$MAJ" ] && MAJ=$m
  done
  sleep 20
done
wait $RP; RC=$?
T1=$(date +%s)
SWPIN1=$(awk '/^pswpin/ {print $2}' /proc/vmstat)
grep -q "reuse-flatten\] using existing $W/" "$SO/cachetest_g8.render.log" \
  || { say "CACHE_CHECK_FAILED reuse did not engage -- a re-flatten ran, strips are NOT comparable"; exit 2; }
[ "$RC" -eq 0 ] || { say "CACHE_CHECK_FAILED render rc=$RC"; exit 1; }

# ---- verdict: every strip byte-identical, or not -----------------------------------------------
python3 - "$REF" "$W" "$OUTJSON" "$((T1-T0))" "$HWM" "$MAJ" "$((SWPIN1-SWPIN0))" "$SAW_FLAG" "$GB" <<'EOF'
import filecmp, json, sys
from pathlib import Path
ref, w, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
secs, hwm_kb, majflt, swpin_pages, saw, gb = map(int, sys.argv[4:10])
pairs = []
for sub in ("meshes/ink", "meshes/concat/w120-129_flat/ink"):
    names = sorted(p.name for p in (ref / sub).iterdir())
    got = sorted(p.name for p in (w / sub).iterdir()) if (w / sub).is_dir() else []
    for n in sorted(set(names) | set(got)):
        a, b = ref / sub / n, w / sub / n
        pairs.append({"file": f"{sub}/{n}",
                      "identical": a.is_file() and b.is_file() and filecmp.cmp(a, b, shallow=False)})
ok = bool(pairs) and all(p["identical"] for p in pairs) and saw == 1
res = {
    "question": "does --cache-gb %d leave every render output byte-identical?" % gb,
    "reference": str(ref), "arm": str(w),
    "flag_seen_on_sampler_cmdline": bool(saw),
    "files_compared": len(pairs),
    "files_identical": sum(p["identical"] for p in pairs),
    "verdict": "IDENTICAL" if ok else "NOT_IDENTICAL",
    "render_wall_s": secs, "render_wall_h": round(secs / 3600, 2),
    "baseline_render_wall_h": {"flat_study_zero": 1.74, "flat_study_in": 1.71, "flat_study_out": 1.86},
    "sampler_peak_rss_gb": round(hwm_kb / 1048576, 2),
    "sampler_major_faults": majflt,
    "box_swap_in_gb": round(swpin_pages * 4096 / 2**30, 2),
    "files": pairs,
}
out.write_text(json.dumps(res, indent=1) + "\n")
print(f"CACHE_CHECK_DONE verdict={res['verdict']} {res['files_identical']}/{res['files_compared']} "
      f"identical, wall {res['render_wall_h']} h, peak {res['sampler_peak_rss_gb']} GB, "
      f"majflt {majflt}, swap-in {res['box_swap_in_gb']} GB, flag_seen={bool(saw)}")
EOF
