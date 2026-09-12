#!/usr/bin/env bash
# gap133s3 was dropped by the first driver: its wait fired on
# satisfaction_metrics_fitted.json (09:34) but fit_spiral writes the MESHES
# afterwards (09:35), so the mesh check ran a minute too early. Waiting on a file
# is only right if it is the LAST file the job writes -- better still, wait on the
# artifact you actually need. This waits on the meshes themselves, and on
# gap133s2's score so the two renders never overlap in RAM.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
MESHES=$(ls -d "$SO"/*patch_gap133s3/meshes/fitted_gap133s3 2>/dev/null | head -1)

n=$(find "$MESHES" -maxdepth 1 -name 'w12?_spliced_*' 2>/dev/null | wc -l)
[ "$n" -eq 10 ] || { echo "[fail] gap133s3 has $n/10 outer meshes at '$MESHES'"; exit 1; }
echo "[ok] gap133s3 meshes present: $n"

echo "[wait] for gap133s2 to be scored before starting $(date -Is)"
DEADLINE=$(( $(date +%s) + 24*3600 ))
until [ -f "$SO/outer_gap133s2/ink_metric/metrics.json" ]; do
  [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] gap133s2 not scored within 6h"; exit 1; }
  sleep 60
done
echo "[wait] gap133s2 scored, starting gap133s3 $(date -Is)"

# Run from a FROZEN copy: the repo copy is edited during a study, and editing a
# script bash is executing corrupts it mid-run (that is what killed the first
# gap133s2 driver). run_snapshot.sh takes the copy for us.
exec "$REPO/repro/spiral_render/run_snapshot.sh" "$SO" run_outer_arms.sh \
  "$SO" 120 129 "gap133s3=$MESHES"
