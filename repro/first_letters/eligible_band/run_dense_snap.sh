#!/usr/bin/env bash
# Finding 130: snap a twice-denser grid of six of PHerc. 0826's read windings, flatten them, and compare the rendered
# surface with finding 125's against the predicted sheet. Registration:
# docs/preregistration/2026-11-20_first_letters_dense_snap.md. Each step only if the one before exited 0:
#   densify   densify_winding.py x2 on the raw windings of arm outer80, into arm dense2
#   snap      run_snap.sh dense2 (the recipe's snap, defaults)
#   flatten   run_flatten.sh dense2, per winding
#   compare   dense_snap.py compare: geometry only, no render, no ink
# Everything stays under PHerc. 0826's run directory; nothing is uploaded.
#
# usage: run_dense_snap.sh
set -u
export FL_SCROLL=PHerc0826
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
WINDINGS=(w020 w030 w040 w050 w060 w070)
ARM=dense2
[ -e "$R/work/fit_$ARM" ] && { echo "$R/work/fit_$ARM exists: finding 130 runs once" >&2; exit 2; }
BASE=$(fit_meshes outer80) || exit 2
DEST=$R/work/fit_$ARM/densified/meshes/fitted
mkdir -p "$DEST" "$R/logs"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$R/logs/dense_snap_$name.log" 2>&1
  rc=$?
  gate "$ARM" "chain_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

densify() {
  local w
  for w in "${WINDINGS[@]}"; do "$PYW" -I "$HERE/densify_winding.py" "$BASE/$w" "$DEST/$w" --factor 2 || return 1; done
}

flatten() {
  local w
  for w in "${WINDINGS[@]}"; do bash "$HERE/run_flatten.sh" "$ARM" "$w" || return 1; done
}

printf '%s\n' "${WINDINGS[@]}" > "$R/work/windings_$ARM.txt"
step densify densify
step snap env PROCS="${PROCS:-2}" bash "$HERE/run_snap.sh" "$ARM"
step flatten flatten
step compare "$PYW" -I "$HERE/dense_snap.py" compare "$R" "$R/work/dense_snap.json" --windings "${WINDINGS[@]}"
cat "$R/logs/dense_snap_compare.log"
