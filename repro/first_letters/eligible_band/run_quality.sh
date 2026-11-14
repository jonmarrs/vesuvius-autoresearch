#!/usr/bin/env bash
# The sheet-following score of one fit arm's raw windings (band_fit_quality.py). Measured once per arm.
#
# usage: run_quality.sh ARM        writes R/work/quality_ARM.json
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_quality.sh full|smoke}
MESHES=$(fit_meshes "$ARM") || exit 2
"$PY" -I "$HERE/band_fit_quality.py" "$R/work/quality_$ARM.json" "$SDT" "$MESHES"
