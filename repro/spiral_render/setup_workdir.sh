#!/usr/bin/env bash
# Build a work directory for run_render.sh from a fitted-mesh folder.
set -euo pipefail
W="${1:?usage: setup_workdir.sh <workdir> <fitted_meshes_dir> [winding...]}"
MESHES="${2:?}"; shift 2
VILLA="${VILLA:-/home/jon/openclaw-workspace/Neo-VM/villa-spiral}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$W/meshes" "$W/inkcache"
if [ "$#" -gt 0 ]; then for w in "$@"; do cp -r "$MESHES"/w${w}_spliced_* "$W/meshes/"; done
else cp -r "$MESHES"/*_spliced_* "$W/meshes/"; fi
# spiral-fitting must be recent enough to have --remote-url; lasagna and
# vesuvius/src are siblings it needs.
git -C "$VILLA" archive origin/main spiral-fitting lasagna vesuvius/src | tar -x -C "$W"
cp -r "$HERE/bin" "$W/bin"; chmod +x "$W"/bin/*
echo "work dir ready: $W"
