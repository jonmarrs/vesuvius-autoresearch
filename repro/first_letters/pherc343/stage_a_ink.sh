#!/usr/bin/env bash
# Kill test stage A: the four released ink models at depth d = +1 only, on the plain and the padded
# render (8 jobs, 16 maps) - the only depth the published image shows. The full recipe runs
# d = -15..+15 (496 jobs) to pool per-model statistics; stage A takes those statistics from the
# published sidecar instead, so it checks the compute chain at 1/31 of the GPU time.
#
# Uses the cloned repo's run_depth_sweep.sh / run_ink.sh unchanged. One villa job and one Hecate job
# at a time (the repo's default). GPU memory is sampled every 5 s so the peak can be reported.
set -uo pipefail
B=/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_repro
N=concat_w047-w048_R5B2_z9500-11000
S=$B/src/repo/ink/scripts
D=${STAGE_D:-1}
export CKPT_DIR=$B/ckpt PY=$B/venv/bin/python TMPDIR=$B/work/tmp PYTHONNOUSERSITE=1
export P_VILLA=${P_VILLA:-1} P_HEC=${P_HEC:-1}
mkdir -p "$TMPDIR"
echo "STAGEA_START $(date -Is) d=$D P_VILLA=$P_VILLA P_HEC=$P_HEC"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 > "$B/logs/stage_a_gpu.csv" &
SMI=$!
rc=0
t0=$(date +%s)
bash "$S/run_depth_sweep.sh" "$B/work/${N}_66.zarr" "$B/work/maps_plain" "$D" "$D" || rc=1
t1=$(date +%s)
bash "$S/run_depth_sweep.sh" "$B/work/${N}_66_padded.zarr" "$B/work/maps_padded" "$D" "$D" || rc=1
t2=$(date +%s)
kill "$SMI" 2>/dev/null
echo "STAGEA_SECONDS plain=$((t1 - t0)) padded=$((t2 - t1))"
cat "$B/work/maps_plain/logs/timings.tsv" "$B/work/maps_padded/logs/timings.tsv"
echo "STAGEA_EXIT $rc $(date -Is)"
echo STAGEA_DONE
exit "$rc"
