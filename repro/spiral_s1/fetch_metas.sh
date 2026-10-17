#!/usr/bin/env bash
# Fetch verified_patches/*/meta.json so patches can be selected by z-ROI.
# Resumable: skips non-empty existing files, and each file goes to a .part until
# it is complete, so an interrupted run leaves nothing to skip. Polite: 10
# concurrent. Reads patch_dirs.txt (one verified_patches/ directory name per
# line) from beside this script; that list is not in the repository.
# metas_misses.txt holds this run's misses only: a re-run retries every miss.
set -u
B=https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/verified_patches
D="$(cd "$(dirname "$0")" && pwd)"
export B D
mkdir -p "$D/metas"
: > "$D/metas_misses.txt"
one() {
  n="${1%/}"
  o="$D/metas/$n.json"
  [ -s "$o" ] && return 0
  curl -sf --max-time 30 --retry 3 --retry-delay 2 -o "$o.part" "$B/$n/meta.json" \
    && mv -f "$o.part" "$o" \
    || { rm -f "$o.part"; echo "MISS $n" >> "$D/metas_misses.txt"; }
}
export -f one
sed 's:/$::' "$D/patch_dirs.txt" | xargs -P 10 -I{} bash -c 'one "$@"' _ {}
echo "DONE $(date -Is)  fetched=$(ls -1 $D/metas | grep -vc '\.part$')  misses=$(wc -l < $D/metas_misses.txt)"
