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
#
# That warning was here, addressed to a human, and it did not work. On 2026-09-11
# a submodule bump moved origin/main mid-corpus and split the arms across two
# render versions; on 2026-09-14 a BACKGROUND MONITOR fetched and moved it again
# while a study was mid-flight. A comment cannot stop an automated job.
#
# So the ref is now resolved to a SHA once, recorded in the work dir as
# VILLA_SHA, and overridable. Set VILLA_REF to a fixed commit for the whole of a
# multi-arm study and every arm provably shares a tree; leave it and at least the
# provenance is auditable afterwards instead of being reconstructed from file
# mtimes, which is how the 09-11 split was eventually found.
VILLA="${VILLA:-/home/jon/openclaw-workspace/Neo-VM/villa-spiral}"
VILLA_REF="${VILLA_REF:-origin/main}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$W/meshes" "$W/inkcache"
if [ "$#" -gt 0 ]; then for w in "$@"; do cp -r "$MESHES"/w${w}_spliced_* "$W/meshes/"; done
else cp -r "$MESHES"/*_spliced_* "$W/meshes/"; fi
# spiral-fitting must be recent enough to have --remote-url; lasagna and
# vesuvius/src are siblings it needs.
VILLA_SHA="$(git -C "$VILLA" rev-parse "$VILLA_REF")"
git -C "$VILLA" archive "$VILLA_SHA" spiral-fitting lasagna vesuvius/src | tar -x -C "$W"
# Written before anything else can fail, so even a work dir from a crashed render
# says what it was built from.
printf '%s\n' "$VILLA_SHA" > "$W/VILLA_SHA"
echo "[setup_workdir] villa $VILLA_REF -> $VILLA_SHA" >&2
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
