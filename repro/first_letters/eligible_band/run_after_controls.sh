#!/usr/bin/env bash
# Run a band read with the choices that findings 131, 132 and 134 decide, read from their records when it starts
# (finding 133's registration and its amendment 1 fix the rule before any of these verdicts exists):
#   STUDIO_SKIP_EMPTY=1  if finding 132's record (CTRL/work/studio_fast.json) has verdict SKIP_ADOPTED, else 0;
#   FL_DENSIFY=2         unless finding 131's record (CTRL/work/dense_read.json) has verdict DENSE_READS_WORSE,
#                        when it is left unset and the raw selected windings are read (arm full);
#   FL_SNAP_PASSES=3     if finding 134's record (CTRL/work/snap_passes.json) has consequence three_passes and
#                        FL_DENSIFY is set (finding 134 tests three passes of the densified windings), else 1.
# A missing or unreadable record leaves its choice at finding 129's: the winner's inference.py, FL_DENSIFY=2, one
# snap pass.
# The choices and the records they came from are printed first, then COMMAND runs with them in its environment.
#
# usage: [FL_CONTROL_DIR=DIR] run_after_controls.sh COMMAND...
set -u
[ "$#" -ge 1 ] || { echo "usage: run_after_controls.sh COMMAND..." >&2; exit 2; }
CTRL=${FL_CONTROL_DIR:-${FL_ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters}/pherc0211_control}

field() {  # RECORD KEY: the record's value for KEY, or "missing"
  local v
  v=$(python3 -I -c 'import json, sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$1" "$2" 2>/dev/null) || v=
  echo "${v:-missing}"
}

V132=$(field "$CTRL/work/studio_fast.json" verdict)
V131=$(field "$CTRL/work/dense_read.json" verdict)
C134=$(field "$CTRL/work/snap_passes.json" consequence)
if [ "$V132" = SKIP_ADOPTED ]; then export STUDIO_SKIP_EMPTY=1; else export STUDIO_SKIP_EMPTY=0; fi
if [ "$V131" = DENSE_READS_WORSE ]; then unset FL_DENSIFY; else export FL_DENSIFY=2; fi
if [ "$C134" = three_passes ] && [ -n "${FL_DENSIFY:-}" ]; then export FL_SNAP_PASSES=3; else export FL_SNAP_PASSES=1; fi
echo "CONTROLS finding_132=$V132 finding_131=$V131 finding_134=$C134 -> STUDIO_SKIP_EMPTY=$STUDIO_SKIP_EMPTY FL_DENSIFY=${FL_DENSIFY:-unset} FL_SNAP_PASSES=$FL_SNAP_PASSES $(date -Is)"
exec "$@"
