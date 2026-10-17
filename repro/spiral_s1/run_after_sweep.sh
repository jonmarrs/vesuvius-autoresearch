#!/usr/bin/env bash
set -u
D="$(cd "$(dirname "$0")" && pwd)"
R=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
while pgrep -f fetch_metas.sh > /dev/null; do sleep 30; done
echo "sweep finished $(date -Is); metas=$(ls -1 $D/metas|wc -l)"
# A failed selection must not fall through to a patches_in_roi.txt left by an earlier run.
cd "$R" && uv run python scripts/select_spiral_patches.py || { echo "selection failed; stopping"; exit 1; }
[ -s "$D/patches_in_roi.txt" ] || { echo "no fetch list written; stopping"; exit 1; }
echo "launching patch fetch: $(wc -l < $D/patches_in_roi.txt) patches"
bash "$D/fetch_patches.sh"
