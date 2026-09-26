#!/usr/bin/env bash
# Amendment 2026-09-26 to docs/preregistration/2026-09-25_sampler_from_source.md: re-run the two
# SOURCE arms only (smp_pub completed and is kept).
#
# Why the first attempt died: with --remote-url (which villa's render_ink.py passes), the 75c79ac5f
# sampler ignores --volume (our pre-filled inkcache) and streams the zarr into VC3D's remote cache
# root, $HOME/.VC3D/remote_cache when no VC3D.ini / /volpkgs / /ephemeral exists. In a --rm container
# HOME is /home/ubuntu, discarded each run, so every run re-streamed the ROI from S3 (2/35 bands in
# 8 min) and the process was SIGKILLed at 16 min (exit 137, cause unconfirmed).
#
# Change, source arms only: HOME -> a persistent host dir (so streamed chunks persist: arm a cold,
# arm b warm), and a hard --memory cap so an overrun fails inside the container rather than via the
# host OOM killer. Cache size is NOT changed (default 16 GB, as in smp_pub). The sampler binary, the
# flat surface, the Python stage and the scorer are unchanged.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
HERE="$(cd "$(dirname "$0")" && pwd)"
REF=$SO/detfit_up1
SRC_IMG=vc-render:sampler-75c79ac5f
SHA=75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3
VCHOME=$SO/vc3d_src_home
MEM_CAP=24g
export RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
export INK_METRIC_SERIAL_FOLDS=1
export RENDER_REUSE_FLATTEN=1
unset FLATTEN_DETERMINISTIC
say() { echo "$*  $(date -Is)"; }
flat_md5() { cat "$1"/meshes/concat/w120-129_flat/[xyz].tif | md5sum | cut -d' ' -f1; }

for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && { say "SMP_ABORTED a render is already running"; exit 3; }; done
[ -f "$SO/smp_pub/ink_metric/metrics.json" ] || { say "SMP_ABORTED smp_pub has no result"; exit 3; }
IMG_SHA=$(docker run --rm --entrypoint cat "$SRC_IMG" /opt/vcsrc/SAMPLER_SHA)
[ "$IMG_SHA" = "$SHA" ] || { say "SMP_ABORTED image sampler sha $IMG_SHA != $SHA"; exit 3; }
mkdir -p "$VCHOME"
REF_MD5=$(flat_md5 "$REF")

# keep the failed first attempt as evidence, never delete it
for N in smp_src_a smp_src_b; do
  [ -e "$SO/$N" ] && { [ -e "$SO/${N}_attempt1" ] && { say "SMP_ABORTED ${N}_attempt1 exists"; exit 5; }; mv "$SO/$N" "$SO/${N}_attempt1"; }
  [ -e "$SO/$N.render.log" ] && mv "$SO/$N.render.log" "$SO/${N}_attempt1.render.log"
done

for N in smp_src_a smp_src_b; do
  W=$SO/$N
  cp -a "$REF" "$W"
  rm -rf "$W/meshes/ink" "$W/ink_metric" "$W/meshes/ink_metric"
  patch -p1 -d "$W" --batch -i "$HERE/reuse_flatten.patch" >/dev/null || { say "PATCH_FAILED $N"; exit 1; }
  flat_md5 "$W" > "$W/FLAT_MD5"
  echo "$REF_MD5" > "$W/REF_FLAT_MD5"
  cat > "$W/bin/vc_render_tifxyz" <<EOF
#!/bin/sh
# SOURCE-built sampler ($SHA). HOME is persistent so its remote cache survives between arms.
exec docker run --rm --user "\$(id -u):\$(id -g)" --memory $MEM_CAP -e HOME=$VCHOME \\
  -v /home/jon/openclaw-workspace:/home/jon/openclaw-workspace \\
  --entrypoint vc_render_tifxyz $SRC_IMG --scale-segmentation 4 "\$@"
EOF
  chmod +x "$W/bin/vc_render_tifxyz"
  printf '%s image_id=%s home=%s mem=%s\n' "$IMG_SHA" "$(docker image inspect "$SRC_IMG" --format '{{.Id}}')" "$VCHOME" "$MEM_CAP" > "$W/SAMPLER"
  say "BUILT $N"
done

cd "$HERE"
for N in smp_src_a smp_src_b; do
  W=$SO/$N; LOG=$SO/$N.render.log
  say "=========== ARM $N starting ==========="
  VENV="$RENDER_VENV" ./run_render.sh "$W" > "$LOG" 2>&1 &
  RP=$!
  ok=
  for i in $(seq 1 60); do
    sleep 5
    grep -q "reuse-flatten\] using existing $W/" "$LOG" && { ok=1; break; }
    grep -q "reuse-flatten\] RENDER_REUSE_FLATTEN=1 but" "$LOG" && break
    kill -0 $RP 2>/dev/null || break
  done
  [ -n "$ok" ] || { say "GUARD_FAILED $N: reuse-flatten did not engage; killing"; kill $RP 2>/dev/null; exit 2; }
  touch "$W/REUSE_OK"
  say "GUARD_OK $N"
  wait $RP || { say "RENDER_FAILED $N (see $LOG)"; exit 1; }
  ./score_arms.sh "$W" >> "$LOG" 2>&1 || { say "SCORE_FAILED $N"; exit 1; }
  [ -f "$W/ink_metric/metrics.json" ] || { say "SCORE_FAILED $N: no metrics.json"; exit 1; }
  say "ARM_DONE $N"
done
say "SAMPLER_RERUN_DONE"
