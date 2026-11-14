#!/usr/bin/env bash
# Winding spacing against sheet spacing for one fit arm (band_fit_spacing.py). CPU, about 20 minutes.
#
# usage: run_spacing.sh ARM        writes R/work/spacing_ARM.json
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_spacing.sh full|smoke}
MESHES=$(fit_meshes "$ARM") || exit 2
"$PY" -I "$HERE/band_fit_spacing.py" "$R/work/spacing_$ARM.json" "$SDT" "$MESHES"
