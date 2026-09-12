#!/usr/bin/env bash
# Render + score w120-w129 for the two remaining GAP seeds, once gap133s3 has
# finished fitting. Registered in
# docs/preregistration/2026-09-02_gap_fix_ink_six_fits.md.
#
# The wait matches on the fit's own output directory, NOT on a script name:
# pgrep -f <name>.sh also matches the shell that wrote the script and any monitor
# whose pattern mentions it, which deadlocked the previous driver for two hours.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch

# Wait on the fit's OWN OUTPUT FILE, never on a process name. A -f process match
# also matches the shell that wrote this script and any monitor whose pattern
# mentions it; that self-match deadlocked the previous driver for two hours, and
# a pkill using the same pattern killed the shell that issued it.
echo "[wait] for gap133s3 to write its satisfaction json $(date -Is)"
DEADLINE=$(( $(date +%s) + 5*3600 ))
until compgen -G "$SO/*patch_gap133s3/satisfaction_metrics_fitted.json" >/dev/null; do
  [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] gap133s3 did not finish within 5h"; exit 1; }
  sleep 60
done
echo "[wait] fit complete $(date -Is)"

S3=$(ls -d "$SO"/*patch_gap133s3 2>/dev/null | head -1)
if [ -n "$S3" ] && [ -f "$S3/satisfaction_metrics_fitted.json" ]; then
  python3 - "$S3" <<'PY'
import json, sys
s = json.load(open(sys.argv[1] + "/satisfaction_metrics_fitted.json"))["summary"]
sa = s["satisfied_area_fraction"]
print(f"[control] gap133s3 satisfied_area_fraction={sa:.4f} vs BASE max 0.8404 -> "
      f"{'reproduces finding 12' if sa > 0.8404 else 'DOES NOT reproduce, arm FLAGGED'}")
PY
else
  echo "[fail] gap133s3 produced no satisfaction json; the fit did not complete"; exit 1
fi

ARMS=()
for spec in "gap133s2:$(ls -d "$SO"/*patch_gap133s2/meshes/fitted_gap133s2 2>/dev/null)" \
            "gap133s3:$S3/meshes/fitted_gap133s3"; do
  tag="${spec%%:*}"; meshes="${spec#*:}"
  [ -d "$meshes" ] && ARMS+=("$tag=$meshes") || echo "[fail] no meshes for $tag at $meshes"
done
[ "${#ARMS[@]}" -gt 0 ] || { echo "[fail] nothing to render"; exit 1; }

exec "$REPO/repro/spiral_render/run_outer_arms.sh" "$SO" 120 129 "${ARMS[@]}"
