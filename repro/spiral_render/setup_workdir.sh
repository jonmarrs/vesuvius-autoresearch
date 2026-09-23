#!/usr/bin/env bash
# Build a work directory for run_render.sh from a fitted-mesh folder.
set -euo pipefail
W="${1:?usage: setup_workdir.sh <workdir> <fitted_meshes_dir> [winding...]}"
MESHES="${2:?}"; shift 2
# NOTE the provenance: work dirs are built from VILLA's origin/main by default, and
# a fetch silently changes what future work dirs get -- so do NOT fetch mid-study.
# Every arm of a comparison must be built from the same tree.
#
# VILLA DEFAULTS TO THE SUBMODULE, corrected 2026-09-19. It used to default to
# .../Neo-VM/villa-spiral, justified by a comment claiming the submodule "does not
# even contain" villa-spiral's commits. That was false when checked: none of
# villa-spiral's last 60 origin/main commits is missing from the submodule, and the
# three extracted trees at the pinned-tier ref 6847063f are IDENTICAL in both. The
# submodule is a strict superset -- it also has be09a8503, which villa-spiral lacks
# and which every current pinned study renders from.
#
# So the old default could not serve the pin, and a run that set VILLA_REF died
# inside this script with "unknown revision" after preflight had already passed.
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
VILLA="${VILLA:-$(cd "$(dirname "$0")/../../villa" && pwd)}"
VILLA_REF="${VILLA_REF:-origin/main}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$W/meshes" "$W/inkcache"
if [ "$#" -gt 0 ]; then for w in "$@"; do cp -r "$MESHES"/w${w}_spliced_* "$W/meshes/"; done
else cp -r "$MESHES"/*_spliced_* "$W/meshes/"; fi
# spiral-fitting must be recent enough to have --remote-url; lasagna and
# vesuvius/src are siblings it needs.
# WARN LOUDLY WHEN UNPINNED. Moving the default to the submodule (2026-09-19) put
# renders on the one checkout the upstream monitor fetches -- origin/main there moved
# four times on 2026-09-18 alone. The old default was static only because nothing
# fetched it. So an unpinned run is now materially riskier than it was, and silence
# is the wrong response to the exact condition that split this project's corpus twice.
if [ "$VILLA_REF" = "origin/main" ] && [ -z "${VILLA_REF_EXPLICIT:-}" ]; then
  echo "[setup_workdir] WARNING: VILLA_REF unset, following origin/main -- a MOVING ref." >&2
  echo "[setup_workdir]   The upstream monitor fetches this checkout; arms built minutes" >&2
  echo "[setup_workdir]   apart can differ. Set VILLA_REF=<sha> for the whole of a study." >&2
fi
VILLA_SHA="$(git -C "$VILLA" rev-parse "$VILLA_REF")"
git -C "$VILLA" archive "$VILLA_SHA" spiral-fitting lasagna vesuvius/src | tar -x -C "$W"
# Written before anything else can fail, so even a work dir from a crashed render
# says what it was built from.
printf '%s\n' "$VILLA_SHA" > "$W/VILLA_SHA"
# THE RENDER HAS A SECOND PIN. VILLA_SHA covers the Python stage (render_ink.py,
# lasagna, scoring). vc_render_tifxyz -- the C++ sampler that reads the ink volume
# -- is built INTO the docker image from a DIFFERENT villa commit, recorded only
# as ARG VILLA_SHA in the Dockerfile. Found 2026-09-21 when upstream #1828 changed
# volume-cartographer/utils/src/zarr.cpp: every VILLA_SHA file said be09a8503 and
# none of them described the binary that actually samples voxels. Record both.
IMG="${VC_IMAGE:-vc-render:local}"
{ printf 'image=%s\n' "$IMG"
  printf 'image_id=%s\n' "$(docker image inspect "$IMG" --format '{{.Id}}' 2>/dev/null || echo unknown)"
  printf 'image_built=%s\n' "$(docker image inspect "$IMG" --format '{{.Created}}' 2>/dev/null || echo unknown)"
  printf 'image_villa_sha=%s\n' "$(grep -m1 '^ARG VILLA_SHA=' "$HERE/Dockerfile" | cut -d= -f2)"
  # Whether the flatten will be deterministic is provenance too: a deterministic
  # arm and a stock arm are not the same instrument, even on one villa tree.
  printf 'flatten_deterministic=%s\n' "${FLATTEN_DETERMINISTIC:-0}"
} > "$W/RENDER_IMAGE"
echo "[setup_workdir] villa $VILLA_REF -> $VILLA_SHA" >&2
cp -r "$HERE/bin" "$W/bin"; chmod +x "$W"/bin/*
# Opt-in render cache size, baked into THIS work dir and recorded in RENDER_IMAGE.
# Unset (the default) changes nothing. Adopt only after reports/cache_gb_check.json
# reads IDENTICAL for that size, and never partway through a study.
if [ -n "${VC_CACHE_GB:-}" ]; then
  "$HERE/set_cache_gb.sh" "$W" "$VC_CACHE_GB" || { echo "FAILED to set --cache-gb" >&2; exit 1; }
fi
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
