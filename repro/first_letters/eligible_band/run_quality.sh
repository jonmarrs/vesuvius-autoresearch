#!/usr/bin/env bash
# The sheet-following score of one fit arm's raw windings (band_fit_quality.py). Measured once per arm.
#
# usage: run_quality.sh ARM        writes R/work/quality_ARM.json
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_quality.sh full|smoke}
found=()
for d in "$R/work/fit_$ARM"/*/meshes/*/; do
  case "$d" in *_spliced/) continue ;; esac
  [ -d "$d" ] && found+=("${d%/}")
done
[ "${#found[@]}" -eq 1 ] || { echo "expected one mesh folder under $R/work/fit_$ARM/*/meshes, found ${#found[@]}" >&2; exit 2; }
"$PY" -I "$HERE/band_fit_quality.py" "$R/work/quality_$ARM.json" "$SDT" "${found[0]}"
