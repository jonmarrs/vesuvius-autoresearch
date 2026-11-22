#!/usr/bin/env bash
# Finding 120: Reader V3 on finding 118's render of the winning PHerc. 211 surface, depths -3 to +2, both layer
# orders. The call is the PHerc. 343 recipe's own call for its ink_9um seeds (ink/scripts/run_ink.sh, villa
# branch): the same villa, flags and 17-layer window s..s+16 with s = depth + 25, with only the checkpoint
# changed, which is how Reader V3's README says to run it. The render is presented as level 0 only, as the recipe
# does. Maps go to C/work/maps_reader_v3/v9 as <render>__reader_v3__L66s<s>{,_reverse}.tif.
#
# usage: run_reader_v3.sh        (after fetch_reader_v3.sh)
set -u
. "$(dirname "$0")/env.sh"
CK=$C/inputs/reader_v3/reader-v3.pth
OUT=$C/work/maps_reader_v3/$SEG_NAME
LO=-3; HI=2; N=66
[ -s "$CK" ] || { echo "no checkpoint at $CK: run fetch_reader_v3.sh" >&2; exit 2; }
[ -d "$RENDER/0" ] || { echo "no render at $RENDER" >&2; exit 2; }
[ -e "$OUT" ] && { echo "$OUT exists: the maps are made once" >&2; exit 2; }
NAME=$(basename "$RENDER" .zarr)
T=$(mktemp -d "$C/work/tmp/reader_v3.XXXXXX") || exit 2
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/l0.zarr" "$OUT" "$OUT/logs"
echo '{"zarr_format": 2}' > "$T/l0.zarr/.zgroup"
ln -s "$RENDER/0" "$T/l0.zarr/0"
echo "V3_START $(date -Is) depths=$LO..$HI"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 \
  > "$C/logs/reader_v3_gpu.csv" &
SMI=$!
t0=$(date +%s)
rc=0
for d in $(seq "$LO" "$HI"); do
  S=$(( N / 2 + d - 8 )); E=$(( S + 17 ))
  t1=$(date +%s)
  (cd "$T" && env -u PYTHONPATH PYTHONNOUSERSITE=1 TMPDIR="$T" "$B/venv/bin/python" \
      -m vesuvius.ink_detection.inference.infer "$T/l0.zarr" "$CK" "$T/out.tif" \
      --overlap 0.5 --blend-mode hann --batch-size "${VILLA_BATCH:-4}" --direction both \
      --layer-start "$S" --layer-end "$E") > "$OUT/logs/d$d.log" 2>&1 || rc=1
  if [ -s "$T/out.tif" ] && [ -s "$T/out_reverse.tif" ]; then
    mv -f "$T/out.tif" "$OUT/${NAME}__reader_v3__L${N}s${S}.tif"
    mv -f "$T/out_reverse.tif" "$OUT/${NAME}__reader_v3__L${N}s${S}_reverse.tif"
  else
    echo "depth $d: no output" >&2; rc=1
  fi
  printf '%s\t%s\t%s\n' "$d" "$(( $(date +%s) - t1 ))" "$rc" >> "$OUT/logs/timings.tsv"
  [ "$rc" -eq 0 ] || break
done
kill "$SMI" 2>/dev/null
PEAK=$(cut -d, -f2 "$C/logs/reader_v3_gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
control_gate reader_v3 "$rc" "$(( $(date +%s) - t0 ))" \
  "\"depths\": [$LO, $HI], \"gpu_peak_mib_all_processes\": ${PEAK:-null}"
echo "V3_EXIT $rc $(date -Is)"
exit $rc
