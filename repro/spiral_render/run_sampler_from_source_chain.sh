#!/usr/bin/env bash
# docs/preregistration/2026-09-25_sampler_from_source.md -- three re-samples of detfit_up1's OWN flat
# surface (reused, never re-solved). smp_pub: published sampler; smp_src_a/b: vc_render_tifxyz built
# from villa 75c79ac5f (image vc-render:sampler-75c79ac5f). Only bin/vc_render_tifxyz differs.
# Launch: setsid nohup ./run_sampler_from_source_chain.sh >> <log> 2>&1 < /dev/null & disown
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
HERE="$(cd "$(dirname "$0")" && pwd)"
REF=$SO/detfit_up1
SRC_IMG=vc-render:sampler-75c79ac5f
SHA=75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3
export RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
export INK_METRIC_SERIAL_FOLDS=1
export RENDER_REUSE_FLATTEN=1
unset FLATTEN_DETERMINISTIC   # no flatten runs: the surface is reused
say() { echo "$*  $(date -Is)"; }
flat_md5() { cat "$1"/meshes/concat/w120-129_flat/[xyz].tif | md5sum | cut -d' ' -f1; }

pgrep -x vc_render_tifxy >/dev/null && { say "SMP_ABORTED a render is already running"; exit 3; }
docker image inspect "$SRC_IMG" >/dev/null 2>&1 || { say "SMP_ABORTED image $SRC_IMG missing"; exit 3; }
IMG_SHA=$(docker run --rm --entrypoint cat "$SRC_IMG" /opt/vcsrc/SAMPLER_SHA)
[ "$IMG_SHA" = "$SHA" ] || { say "SMP_ABORTED image sampler sha $IMG_SHA != $SHA"; exit 3; }
REF_MD5=$(flat_md5 "$REF")

for N in smp_pub smp_src_a smp_src_b; do
  W=$SO/$N
  [ -e "$W" ] && { say "SMP_ABORTED $W exists"; exit 5; }
  cp -a "$REF" "$W"
  rm -rf "$W/meshes/ink" "$W/ink_metric" "$W/meshes/ink_metric"
  patch -p1 -d "$W" --batch -i "$HERE/reuse_flatten.patch" >/dev/null \
    || { say "PATCH_FAILED $N"; exit 1; }
  flat_md5 "$W" > "$W/FLAT_MD5"
  echo "$REF_MD5" > "$W/REF_FLAT_MD5"
  if [ "$N" != smp_pub ]; then
    sed -i "s#vc-render:local#$SRC_IMG#" "$W/bin/vc_render_tifxyz"
    grep -q "$SRC_IMG" "$W/bin/vc_render_tifxyz" || { say "WRAPPER_EDIT_FAILED $N"; exit 1; }
    printf '%s image_id=%s\n' "$IMG_SHA" "$(docker image inspect "$SRC_IMG" --format '{{.Id}}')" > "$W/SAMPLER"
  fi
  say "BUILT $N"
done

cd "$HERE"
for N in smp_pub smp_src_a smp_src_b; do
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
  [ -n "$ok" ] || { say "GUARD_FAILED $N: reuse-flatten did not engage; killing"; pkill -TERM -P $RP; kill $RP 2>/dev/null; exit 2; }
  touch "$W/REUSE_OK"
  say "GUARD_OK $N"
  wait $RP || { say "RENDER_FAILED $N (see $LOG)"; exit 1; }
  ./score_arms.sh "$W" >> "$LOG" 2>&1 || { say "SCORE_FAILED $N"; exit 1; }
  [ -f "$W/ink_metric/metrics.json" ] || { say "SCORE_FAILED $N: no metrics.json"; exit 1; }
  say "ARM_DONE $N"
done
say "SAMPLER_CHAIN_DONE"
