#!/usr/bin/env bash
# Build a work directory for run_render.sh from a fitted-mesh folder.
set -euo pipefail
W="${1:?usage: setup_workdir.sh <workdir> <fitted_meshes_dir> [winding...]}"
MESHES="${2:?}"; shift 2
# NOTE the provenance: work dirs are built from THIS checkout's origin/main, which
# is a different thing from the villa SUBMODULE pinned in this repo. They can and
# do differ (villa-spiral is at 5479453a; the submodule has been bumped past it and
# does not even contain that commit). Quote this one when recording what a render
# ran on, and do NOT fetch it mid-study: every arm of a comparison must be built
# from the same tree, and a fetch silently changes what future work dirs get.
VILLA="${VILLA:-/home/jon/openclaw-workspace/Neo-VM/villa-spiral}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$W/meshes" "$W/inkcache"
if [ "$#" -gt 0 ]; then for w in "$@"; do cp -r "$MESHES"/w${w}_spliced_* "$W/meshes/"; done
else cp -r "$MESHES"/*_spliced_* "$W/meshes/"; fi
# spiral-fitting must be recent enough to have --remote-url; lasagna and
# vesuvius/src are siblings it needs.
git -C "$VILLA" archive origin/main spiral-fitting lasagna vesuvius/src | tar -x -C "$W"
cp -r "$HERE/bin" "$W/bin"; chmod +x "$W"/bin/*
# The extracted tree is stock villa, so the serial-fold gate is NOT in it. Applying
# it here, at the one place work dirs are created, is the fix for an outer-winding
# arm that ran three folds concurrently and was OOM-killed while the environment
# said INK_METRIC_SERIAL_FOLDS=1 and nothing was reading it.
# Inert without that variable; see serial_folds.patch and README section 7.
if ! grep -q SERIAL_FOLDS "$W/spiral-fitting/get_ink_metrics.py"; then
  patch -p1 -d "$W" --batch -i "$HERE/serial_folds.patch" \
    || { echo "FAILED to apply serial_folds.patch (villa pin moved?)" >&2; exit 1; }
fi
grep -q SERIAL_FOLDS "$W/spiral-fitting/get_ink_metrics.py" \
  || { echo "serial_folds gate missing after patch" >&2; exit 1; }
echo "work dir ready: $W"
