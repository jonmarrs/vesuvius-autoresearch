# Sourced by the finding-118 scripts. The recipe, its checkpoints, its render image and the scan are the ones the
# eligible-band scripts use for PHerc. 0211; this run's own files live under C, on this machine.
#   C  run directory of the control: inputs/winner (the winning submission's files), work, logs
# shellcheck source=../eligible_band/env.sh
FL_SCROLL=PHerc0211 . "$(dirname "${BASH_SOURCE[0]}")/../eligible_band/env.sh"
C=${FL_CONTROL_DIR:-$FL_ROOT/pherc0211_control}
WINNER=$C/inputs/winner
SEG_NAME=v9
SEG=$WINNER/$SEG_NAME/normalized-tifxyz
RENDER=$C/work/render/${SEG_NAME}_66.zarr
MAPS=$C/work/maps/$SEG_NAME
mkdir -p "$C/work" "$C/logs"

# Record a step's exit code: C/work/gate/STEP.json
control_gate() {  # NAME EXIT SECONDS [EXTRA_JSON_FIELDS]
  mkdir -p "$C/work/gate"
  printf '{"exit": %s, "seconds": %s%s}\n' "$2" "$3" "${4:+, $4}" > "$C/work/gate/$1.json"
}
