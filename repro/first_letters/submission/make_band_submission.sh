#!/usr/bin/env bash
# A First Letters submission image from one winding of a band read, and its control, with the PHerc. 343 recipe's
# make_submission_image.py (MIT, Nieuwlaar/pherc343-first-letters at e8370f1f, run from its clone, unchanged).
#
#   ink        submission_inputs.py ink: Studio's map of layers 41 down to 26 (the reading side) and of the same
#              layers reversed (the control), as the float32 TIFFs the recipe's script reads
#   sums       sha256 of the mesh's geometry files, which the script checks before it draws (--geometry-sums)
#   orient     submission_inputs.py orient: flip_lr and flip_ud by the band pages' rule, from the mesh, the scroll axis
#              and the catalog's two orientation flags, passed to the script as --flip-lr/--flip-ud. The script's own
#              rule assumes PHerc. 343's frame (z bottom to top, right-handed); on PHerc. 211 it turns the image by 180
#              degrees. It gets --umbilicus too only in that frame, where it then checks the flips and stops on a
#              mismatch.
#   image      the submission image: the reading-side map over CT layer d+1 of the winding's 66-layer render, cut to
#              the area, in reading orientation (orient), with a 1 cm scale bar,
#              the row lines, the letter-size table and a sidecar JSON (the recipe's published settings: dimmed-ct,
#              compact caption, letter markers off)
#   stats      submission_inputs.py stats: the reading image's ink and CT stretch, as the control's --ink-stats
#   control    the same area from the reversed-plane map (--allow-blind), drawn with the reading image's numbers and
#              without row lines (the script derives them from the ink): the false-positive control beside it
#   isometry   submission_inputs.py isometry: the flattening's edge stretch, shear and area ratio inside the area
#   manifest   every input's and output's sha256, the recipe's commit and the commands
# The area, the rows and the letter boxes are the only hand-made inputs, as in the recipe; nothing here chooses them.
# The output directory must not exist. An eligible scroll's outputs stay on this machine.
#
# usage: make_band_submission.sh MESH RENDER READING_NPY CONTROL_NPY UMBILICUS AREA ROWS LETTERS OUT \
#          --scroll "PHerc. 0826" --volume-id ID --voxel-um UM --top-to-bottom true|false --left-handed true|false \
#          --render-flipped true|false [--max-cm2 4] [--forbid-words FILE]
#   --top-to-bottom and --left-handed are the scroll's z_direction_is_top_to_bottom and left_handed_coordinates in the
#   open-data catalog's metadata.json; --render-flipped is the band read's orient decision for the winding (flip:
#   rendered with flipped normals, so its layers run outward while the mesh normal points inward; the script then
#   warns that its normal points inward, and the image carries a note saying why).
#   AREA is row0,row1,col0,col1 of the raw render (ends exclusive) or a JSON with raw_render_px.
#   ROWS and LETTERS are the recipe's JSON files, or "-" for a first image without them (to place them on).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
FL_ROOT=${FL_ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters}
RECIPE=${RECIPE:-$FL_ROOT/pherc343_repro/src/repo}
PY343=${PY343:-$FL_ROOT/pherc343_repro/venv/bin/python}
PYW=${PYW:-$ROOT/.venv/bin/python}
RECIPE_COMMIT=e8370f1f88a211166056df62ea6fcfffe4a1063e
[ $# -ge 9 ] || { sed -n '2,20p' "$0" >&2; exit 2; }
MESH=$1 RENDER=$2 READING=$3 CONTROL=$4 UMB=$5 AREA=$6 ROWS=$7 LETTERS=$8 OUT=$9
shift 9
SCROLL= VOLUME= VOXEL= MAXCM2=4 FORBID= TTB= LH= FLIPPED=
while [ $# -gt 0 ]; do
  case $1 in
    --scroll) SCROLL=$2; shift 2 ;;
    --volume-id) VOLUME=$2; shift 2 ;;
    --voxel-um) VOXEL=$2; shift 2 ;;
    --max-cm2) MAXCM2=$2; shift 2 ;;
    --forbid-words) FORBID=$2; shift 2 ;;
    --top-to-bottom) TTB=$2; shift 2 ;;
    --left-handed) LH=$2; shift 2 ;;
    --render-flipped) FLIPPED=$2; shift 2 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
[ -n "$SCROLL" ] && [ -n "$VOLUME" ] && [ -n "$VOXEL" ] || { echo "--scroll, --volume-id and --voxel-um are required" >&2; exit 2; }
for v in "$TTB" "$LH" "$FLIPPED"; do
  case $v in true|false) ;; *) echo "--top-to-bottom, --left-handed and --render-flipped are true or false" >&2; exit 2 ;; esac
done
[ -e "$OUT" ] && { echo "$OUT exists" >&2; exit 2; }
[ "$(git -C "$RECIPE" rev-parse HEAD 2>/dev/null)" = "$RECIPE_COMMIT" ] \
  || { echo "$RECIPE is not the recipe at $RECIPE_COMMIT" >&2; exit 2; }
SCRIPT=$RECIPE/ink/scripts/make_submission_image.py
git -C "$RECIPE" diff --quiet HEAD -- ink/scripts/make_submission_image.py \
  || { echo "$SCRIPT differs from the recipe's commit" >&2; exit 2; }
for f in "$MESH/x.tif" "$MESH/y.tif" "$MESH/z.tif" "$MESH/meta.json" "$READING" "$CONTROL" "$UMB"; do
  [ -f "$f" ] || { echo "missing $f" >&2; exit 2; }
done
STEM=$(basename "$MESH" .tifxyz)
ANNOT=()  # ROWS and LETTERS may be "-": a first image without annotations, to place them on
if [ "$ROWS" != - ]; then [ -f "$ROWS" ] || { echo "missing $ROWS" >&2; exit 2; }; ANNOT+=(--rows "$ROWS"); fi
if [ "$LETTERS" != - ]; then
  [ -f "$LETTERS" ] || { echo "missing $LETTERS" >&2; exit 2; }
  ANNOT+=(--letters "$LETTERS" --letter-markers off --sizes-csv "$OUT/image/${STEM}_letter_sizes.csv")
fi
case $AREA in
  *.json) AREA_RAW=$("$PYW" -I -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d.get("area",d).get("raw_render_px",d); print(",".join(str(int(d[k])) for k in ("row0","row1","col0","col1")))' "$AREA") || exit 2 ;;
  *) AREA_RAW=$AREA ;;
esac
IFS=, read -r ROW0 ROW1 COL0 COL1 <<< "$AREA_RAW"
HW=$("$PY343" -I -c 'import sys, zarr; z = zarr.open(sys.argv[1], mode="r"); z = z["0"] if hasattr(z, "keys") else z; print(*z.shape[1:])' "$RENDER") || exit 2
mkdir -p "$OUT/maps" "$OUT/image" "$OUT/control" "$OUT/logs"

run() {  # NAME COMMAND...: run one step, keep its log, stop on failure
  local name=$1
  shift
  echo "STEP $name $(date -Is)"
  printf '%q ' "$@" > "$OUT/logs/$name.cmd"
  "$@" > "$OUT/logs/$name.log" 2>&1 || { echo "step $name failed: $OUT/logs/$name.log" >&2; exit 1; }
}

# shellcheck disable=SC2086 # HW is "H W"
run ink "$PYW" -I "$HERE/submission_inputs.py" ink "$READING" "$CONTROL" --render-hw $HW --out-dir "$OUT/maps" --stem "$STEM"
(cd "$(dirname "$MESH")" && sha256sum "$STEM.tifxyz"/{x,y,z}.tif $( [ -f "$STEM.tifxyz/mask.tif" ] && echo "$STEM.tifxyz/mask.tif" )) > "$OUT/mesh_geometry.sha256" || exit 1
run orient "$PYW" -I "$HERE/submission_inputs.py" orient "$MESH" --umbilicus "$UMB" --top-to-bottom "$TTB" \
  --left-handed "$LH" --out "$OUT/orientation.json"
read -r FLIP_LR FLIP_UD < <("$PYW" -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(int(d["flip_lr"]), int(d["flip_ud"]))' "$OUT/orientation.json") || exit 1
COMMON=(--mesh "$MESH" --flip-lr "$FLIP_LR" --flip-ud "$FLIP_UD" --ct "$RENDER" --ct-layer d+1 --overlay-style dimmed-ct --caption compact
        --geometry-sums "$OUT/mesh_geometry.sha256" --area "$COL0,$ROW0,$COL1,$ROW1" --max-cm2 "$MAXCM2"
        --voxel-um "$VOXEL" --scroll "$SCROLL" --volume-id "$VOLUME")
[ -n "$FORBID" ] && COMMON+=(--forbid-words "$FORBID")
[ "$TTB" = false ] && [ "$LH" = false ] && COMMON+=(--umbilicus "$UMB")  # the script's own frame: it cross-checks
[ "$FLIPPED" = true ] && COMMON+=(--note "Rendered with flipped normals: layers run outward, d = +1 is outside the surface")
run image "$PY343" -I "$SCRIPT" "${COMMON[@]}" --ink "$OUT/maps/${STEM}__studio__L66zc33.50_reverse.tif" \
  --ink-names studio "${ANNOT[@]}" --out-dir "$OUT/image"
run stats "$PYW" -I "$HERE/submission_inputs.py" stats "$OUT/image/$STEM.json" --out "$OUT/control_ink_stats.json"
run control "$PY343" -I "$SCRIPT" "${COMMON[@]}" --ink "$OUT/maps/${STEM}__studio__L66zc33.50.tif" \
  --ink-names studio --ink-stats "$OUT/control_ink_stats.json" --allow-blind --out-dir "$OUT/control"
run isometry "$PYW" -I "$HERE/submission_inputs.py" isometry "$MESH" --area "$AREA_RAW" --out "$OUT/isometry.json"
run manifest "$PYW" -I - "$OUT" "$RECIPE_COMMIT" "$SCRIPT" "$MESH" "$RENDER" "$READING" "$CONTROL" "$UMB" "$ROWS" "$LETTERS" <<'EOF'
import hashlib, json, sys
from pathlib import Path
out, commit, script, *inputs = sys.argv[1:]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
names = ["mesh", "render", "reading_map", "control_map", "umbilicus", "rows", "letters"]
record = {"recipe_commit": commit, "recipe_script_sha256": sha(script),
          "inputs": {n: {"path": Path(p).name, "sha256": None if (p == "-" or Path(p).is_dir()) else sha(p)} for n, p in zip(names, inputs)},
          "outputs": {str(p.relative_to(out)): sha(p) for p in sorted(Path(out).rglob("*")) if p.is_file() and p.name != "manifest.json"},
          "commands": {p.stem: p.read_text() for p in sorted((Path(out) / "logs").glob("*.cmd"))}}
(Path(out) / "manifest.json").write_text(json.dumps(record, indent=1) + "\n")
EOF
echo "DONE $OUT"
