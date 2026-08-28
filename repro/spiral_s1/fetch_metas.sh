#!/usr/bin/env bash
# Fetch verified_patches/*/meta.json so patches can be selected by z-ROI.
# Resumable: skips non-empty existing files. Polite: 10 concurrent.
set -u
B=https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/verified_patches
D="$(cd "$(dirname "$0")" && pwd)"
export B D
one() {
  n="${1%/}"
  o="$D/metas/$n.json"
  [ -s "$o" ] && return 0
  curl -sf --max-time 30 --retry 3 --retry-delay 2 -o "$o" "$B/$n/meta.json" || { rm -f "$o"; echo "MISS $n" >> "$D/metas_misses.txt"; }
}
export -f one
sed 's:/$::' "$D/patch_dirs.txt" | xargs -P 10 -I{} bash -c 'one "$@"' _ {}
echo "DONE $(date -Is)  fetched=$(ls -1 $D/metas | wc -l)  misses=$(wc -l < $D/metas_misses.txt 2>/dev/null || echo 0)"
