#!/usr/bin/env bash
# Bake a vc_render_tifxyz chunk-cache size into ONE work dir, and record it.
#
#   set_cache_gb.sh <workdir> <GB>
#
# Why: the sampler's remote path caches chunks ONLY in memory, sized by --cache-gb
# (default 16). On this 31 GB box that pushes the render to ~27 GB and into swap
# (reports/holding_the_flatten_fixed_collapses_the_floor.md, 2026-09-22 addendum).
#
# ADOPT ONLY IF the queued byte-identity check says so: reports/cache_gb_check.json
# must read "verdict": "IDENTICAL" for this GB. A cache size that changes any output
# byte is an instrument change. Never change it mid-study: every arm of a study must
# carry the same setting, which is why it is baked into the work dir (its wrapper and
# RENDER_IMAGE) rather than read from the environment at render time.
set -euo pipefail
W="${1:?usage: set_cache_gb.sh <workdir> <GB>}"
GB="${2:?usage: set_cache_gb.sh <workdir> <GB>}"
WRAP="$W/bin/vc_render_tifxyz"
[[ "$GB" =~ ^[1-9][0-9]*$ ]] || { echo "set_cache_gb: GB must be a positive integer, got '$GB'" >&2; exit 2; }
[ -f "$WRAP" ] || { echo "set_cache_gb: no wrapper at $WRAP" >&2; exit 2; }
if grep -q -- '--cache-gb' "$WRAP"; then
  echo "set_cache_gb: $WRAP already sets --cache-gb; refusing to change it" >&2; exit 3
fi
grep -q -- '--scale-segmentation 4 "\$@"' "$WRAP" \
  || { echo "set_cache_gb: wrapper does not have the expected form; not editing" >&2; exit 2; }
sed -i "s|--scale-segmentation 4 \"\\\$@\"|--scale-segmentation 4 --cache-gb $GB \"\$@\"|" "$WRAP"
grep -q -- "--cache-gb $GB \"\$@\"" "$WRAP" || { echo "set_cache_gb: edit did not apply" >&2; exit 1; }
printf 'cache_gb=%s\n' "$GB" >> "$W/RENDER_IMAGE"
echo "set_cache_gb: $W renders with --cache-gb $GB (recorded in RENDER_IMAGE)"
