#!/usr/bin/env bash
# Finding 121: our own fit's windings at the place where PHerc. 211's First Letters prize was won, end to end.
# Registration: docs/preregistration/2026-11-16_first_letters_0211_end_to_end.md. Runs once, unattended, each step
# only if the one before exited 0:
#   snap         the recipe's snap of WINDINGS from finding 119's full fit (arm e2e)
#   flatten      lasagna, per winding
#   orient       end_to_end.py orient: flip or keep per winding, from the geometry against the winner's surface
#   render       66 layers per winding, --flip-normals where orient says flip
#   ink          the recipe's four models at depth +1, both sides, per winding
#   reader_v3    Reader V3 at depth +1, both sides, per winding (described)
#   compare      end_to_end.py compare
# Each step's exit and seconds go to R/work/gate_e2e/chain_<step>.json, beside the band scripts' own records.
#
# usage: run_end_to_end.sh
set -u
export FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150
HERE=$(cd "$(dirname "$0")" && pwd)
BAND=$(cd "$HERE/../eligible_band" && pwd)
. "$HERE/env.sh"  # the band's env (R, B, PY, RECIPE, gate) and finding 118's (C, WINNER, SEG, RENDER, MAPS)
PYW=${PYW:-$(cd "$HERE/../../.." && pwd)/.venv/bin/python}
ARM=e2e
WINDINGS=(w033 w034 w035 w036)
DEPTH=1; N=66
CK=$C/inputs/reader_v3/reader-v3.pth
CK_SHA256=ea405417450abd8ace1b8ff79ebce3adb646c5e48ab95da46844d77efe984d8a
[ -e "$R/work/windings_$ARM.txt" ] && { echo "$R/work/windings_$ARM.txt exists: finding 121 runs once" >&2; exit 2; }
[ -f "$SEG/x.tif" ] && [ -d "$RENDER/2" ] && [ -d "$MAPS" ] || { echo "finding 118's surface, render or maps missing" >&2; exit 2; }
[ -d "$R/work/snap_full" ] || { echo "finding 119's snap is missing" >&2; exit 2; }
mkdir -p "$R/logs" "$C/work/tmp"

step() {  # NAME LOG COMMAND...: run, record the gate, stop the chain on failure
  local name=$1 log=$2 t0 rc
  shift 2
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$log" 2>&1
  rc=$?
  gate "$ARM" "chain_$name" "$rc" "$(( $(date +%s) - t0 ))"  # beside the band scripts' own gates, never over them
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

ink() {  # WINDING: the recipe's four models at depth +1 on its render, both sides
  local render=$R/work/render_$ARM/${1}_66.zarr out=$R/work/maps_$ARM/$1 n
  [ -e "$out" ] && { echo "$out exists" >&2; return 2; }
  mkdir -p "$out"
  env -u PYTHONPATH CKPT_DIR="$B/ckpt" PY="$B/venv/bin/python" TMPDIR="$C/work/tmp" PYTHONNOUSERSITE=1 \
    P_VILLA=1 P_HEC=1 bash "$RECIPE/ink/scripts/run_depth_sweep.sh" "$render" "$out" "$DEPTH" "$DEPTH" || return 1
  n=$(find "$out" -maxdepth 1 \( -name "${1}_66__*.tif" -o -name "${1}_66__*.png" \) | wc -l)
  [ "$n" -ge 8 ] || { echo "only $n of 8 maps in $out" >&2; return 1; }
}

reader_v3() {  # WINDING: Reader V3 at depth +1 on its render, both sides (run_reader_v3.sh's call, one depth)
  local render=$R/work/render_$ARM/${1}_66.zarr out=$R/work/maps_${ARM}_v3 t s e
  s=$(( N / 2 + DEPTH - 8 )); e=$(( s + 17 ))
  echo "$CK_SHA256  $CK" | sha256sum -c --quiet || return 1
  "$B/venv/bin/python" -I "$HERE/check_checkpoint.py" "$CK" || return 1
  t=$(mktemp -d "$C/work/tmp/e2e_v3.XXXXXX") || return 1
  mkdir -p "$t/l0.zarr" "$out"
  echo '{"zarr_format": 2}' > "$t/l0.zarr/.zgroup"
  ln -s "$render/0" "$t/l0.zarr/0"
  (cd "$t" && env -u PYTHONPATH PYTHONNOUSERSITE=1 TMPDIR="$t" "$B/venv/bin/python" \
      -m vesuvius.ink_detection.inference.infer "$t/l0.zarr" "$CK" "$t/out.tif" \
      --overlap 0.5 --blend-mode hann --batch-size "${VILLA_BATCH:-4}" --direction both \
      --layer-start "$s" --layer-end "$e") || { rm -rf "$t"; return 1; }
  if [ -s "$t/out.tif" ] && [ -s "$t/out_reverse.tif" ]; then
    mv -f "$t/out.tif" "$out/${1}_66__reader_v3__L${N}s${s}.tif"
    mv -f "$t/out_reverse.tif" "$out/${1}_66__reader_v3__L${N}s${s}_reverse.tif"
  else
    echo "no Reader V3 output for $1" >&2; rm -rf "$t"; return 1
  fi
  rm -rf "$t"
}

printf '%s\n' "${WINDINGS[@]}" > "$R/work/windings_$ARM.txt"
ln -sfn fit_full "$R/work/fit_$ARM"  # the same fit as finding 119; fit_meshes reads it under this arm's name
step snap "$R/logs/snap_$ARM.log" bash "$BAND/run_snap.sh" "$ARM"
for w in w034 w035 w036; do  # described: the recipe's snap is deterministic (finding 119's windings again)
  same=yes
  for f in x y z; do cmp -s "$R/work/snap_$ARM/$w/$f.tif" "$R/work/snap_full/$w/$f.tif" || same=no; done
  echo "$w $same"
done > "$R/work/${ARM}_snap_same_as_finding_119.txt"
for w in "${WINDINGS[@]}"; do
  step "flatten_$w" "$R/logs/flatten_${ARM}_$w.log" bash "$BAND/run_flatten.sh" "$ARM" "$w"
done
FINALS=()
for w in "${WINDINGS[@]}"; do FINALS+=("$R/work/final_$ARM/$w.tifxyz"); done
step orient "$R/logs/${ARM}_orient.log" "$PYW" -I "$HERE/end_to_end.py" orient "$R/work/${ARM}_orient.json" "$SEG" "${FINALS[@]}"
OURS=()
for w in "${WINDINGS[@]}"; do
  how=$(awk -v n="$w.tifxyz" '$1 == n {print $2}' "$R/logs/${ARM}_orient.log")
  case "$how" in
    flip) step "render_$w" "$R/logs/render_${ARM}_$w.log" bash "$BAND/run_render.sh" "$ARM" "$w" flip
          OURS+=(--ours-flipped) ;;
    keep) step "render_$w" "$R/logs/render_${ARM}_$w.log" bash "$BAND/run_render.sh" "$ARM" "$w"
          OURS+=(--ours) ;;
    *) echo "no orientation for $w" >&2; gate "$ARM" "chain_render_$w" 2 0; exit 2 ;;
  esac
  OURS+=("$R/work/final_$ARM/$w.tifxyz" "$R/work/maps_$ARM/$w" "$R/work/render_$ARM/${w}_66.zarr")
done
for w in "${WINDINGS[@]}"; do step "ink_$w" "$R/logs/ink_${ARM}_$w.log" ink "$w"; done
for w in "${WINDINGS[@]}"; do step "reader_v3_$w" "$R/logs/reader_v3_${ARM}_$w.log" reader_v3 "$w"; done
step compare "$R/logs/${ARM}_compare.log" "$PYW" -I "$HERE/end_to_end.py" compare "$R/work/${ARM}_compare.json" \
  --winner-mesh "$SEG" --winner-maps "$MAPS" --winner-render "$RENDER" \
  --studio "$WINNER/download/v9_studiosoft_probability_f32.tif" --studio-mask "$WINNER/v9/studiosoft-mask.png" \
  "${OURS[@]}" --v3-maps "$R/work/maps_${ARM}_v3" --image "$R/work/${ARM}_v9.png"
cat "$R/logs/${ARM}_compare.log"
