#!/usr/bin/env bash
# P1 and P2 on the final (snapped and flattened) windings: the registered distance from each published
# winding to them, and whether their normals point the same way as the published ones.
#
# usage: run_p1.sh ARM              writes R/work/final_select_ARM.json
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_p1.sh recipe|reduced}
case "$ARM" in recipe|reduced) ;; *) echo "P1 is for the registered arms only" >&2; exit 2 ;; esac
OUT=$R/work/final_select_$ARM.json
[ -e "$OUT" ] && { echo "$OUT exists: P1 is measured once" >&2; exit 2; }
FINAL=()
while read -r w; do
  [ -f "$R/work/final_$ARM/$w.tifxyz/x.tif" ] || { echo "no final winding for $w" >&2; exit 2; }
  FINAL+=("$R/work/final_$ARM/$w.tifxyz")
done < "$R/work/windings_$ARM.txt"
"$PY" -I "$HERE/mesh_step_analysis.py" select "$OUT" \
  --published "w047=$PUBLISHED_W047" "w048=$PUBLISHED_W048" --candidates "${FINAL[@]}"
