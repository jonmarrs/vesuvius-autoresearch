#!/usr/bin/env bash
# Render + score w120-w129 for the three remaining honest seeds, sequentially.
# Registered in docs/preregistration/2026-09-01_outer_winding_noise_floor.md.
# Sequential because vc_render_tifxyz peaks near 26GB on a 32GB box.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch

declare -A FIT=(
  [seed02]=2026-08-29_s1_slice-13056-18432_38442-patch_seed02
  [seed03]=2026-08-31_s1_slice-13056-18432_38442-patch_seed03
  [seed04]=2026-08-31_s1_slice-13056-18432_38442-patch_seed04
)

for S in seed02 seed03 seed04; do
  W="$SO/outer_$S"
  echo "=================== ARM $S $(date -Is) ==================="
  if [ -f "$W/ink_metric/metrics.json" ]; then echo "[skip] $S already scored"; continue; fi
  if [ ! -d "$W/meshes" ]; then
    "$REPO/repro/spiral_render/setup_workdir.sh" "$W" \
      "$SO/${FIT[$S]}/meshes/fitted_$S" 120 121 122 123 124 125 126 127 128 129 \
      || { echo "[fail] setup $S"; continue; }
  fi
  n=$(ls -d "$W"/meshes/w12?_spliced_* 2>/dev/null | wc -l)
  echo "[check] $S has $n spliced meshes (expect 10)"
  [ "$n" -eq 10 ] || { echo "[fail] wrong mesh count for $S"; continue; }

  echo "[render] $S $(date -Is)"
  "$REPO/repro/spiral_render/run_render.sh" "$W" > "$SO/outer_${S}_render.log" 2>&1
  echo "[render] $S rc=$? $(date -Is)"
  ls "$W"/meshes/ink/*.jpg >/dev/null 2>&1 || { echo "[fail] no strips for $S"; continue; }

  echo "[score] $S $(date -Is)"
  "$REPO/repro/spiral_render/score_arms.sh" "$W" >> "$SO/outer_${S}_render.log" 2>&1
  echo "[score] $S rc=$? $(date -Is)"
done
echo "=================== SEEDS DONE $(date -Is) ==================="
