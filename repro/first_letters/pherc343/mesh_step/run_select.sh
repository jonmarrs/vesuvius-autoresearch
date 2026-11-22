#!/usr/bin/env bash
# Choose, by geometry alone, the raw fitted winding nearest each published winding (registered rule:
# smallest median distance among candidates covering at least half of the published winding).
# Run once per arm, and only after the registration is committed. Refused for the smoke arm, whose
# windings are never compared with the published ones.
#
# usage: run_select.sh ARM          writes R/work/select_ARM.json and R/work/windings_ARM.txt
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_select.sh recipe|reduced}
case "$ARM" in recipe|reduced) ;; *) echo "selection is for the registered arms only" >&2; exit 2 ;; esac
OUT=$R/work/select_$ARM.json
[ -e "$OUT" ] && { echo "$OUT exists: the selection is made once" >&2; exit 2; }
MESHES=$(fit_meshes "$ARM") || exit 2
CANDIDATES=()
for d in "$MESHES"/w*/; do
  case "$d" in *_spliced/) continue ;; esac
  [ -f "$d/x.tif" ] && CANDIDATES+=("${d%/}")
done
echo "SELECT_START $(date -Is) ${#CANDIDATES[@]} candidates under $MESHES"
"$PY" -I "$HERE/mesh_step_analysis.py" select "$OUT" \
  --published "w047=$PUBLISHED_W047" "w048=$PUBLISHED_W048" --candidates "${CANDIDATES[@]}" || exit 1
"$PY" -I -c '
import json, sys
chosen = [e["chosen"] for e in json.load(open(sys.argv[1]))["published"].values() if e["chosen"]]
open(sys.argv[2], "w").write("".join(name + "\n" for name in sorted(set(chosen))))
print("chosen:", sorted(set(chosen)))' "$OUT" "$R/work/windings_$ARM.txt"
echo "SELECT_EXIT $? $(date -Is)"
