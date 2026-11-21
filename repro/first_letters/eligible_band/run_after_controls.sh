#!/usr/bin/env bash
# Run a band read with the two choices that findings 131 and 132 decide, read from their records when it starts
# (finding 133's registration fixes the rule before either verdict exists):
#   STUDIO_SKIP_EMPTY=1  if finding 132's record (CTRL/work/studio_fast.json) has verdict SKIP_ADOPTED, else 0;
#   FL_DENSIFY=2         unless finding 131's record (CTRL/work/dense_read.json) has verdict DENSE_READS_WORSE,
#                        when it is left unset and the raw selected windings are read (arm full).
# A missing or unreadable record leaves its choice at finding 129's: the winner's inference.py, FL_DENSIFY=2.
# The choices and the records they came from are printed first, then COMMAND runs with them in its environment.
#
# usage: [FL_CONTROL_DIR=DIR] run_after_controls.sh COMMAND...
set -u
[ "$#" -ge 1 ] || { echo "usage: run_after_controls.sh COMMAND..." >&2; exit 2; }
CTRL=${FL_CONTROL_DIR:-${FL_ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters}/pherc0211_control}

verdict() {  # RECORD: the record's verdict, or "missing"
  local v
  v=$(python3 -I -c 'import json, sys; print(json.load(open(sys.argv[1]))["verdict"])' "$1" 2>/dev/null) || v=
  echo "${v:-missing}"
}

V132=$(verdict "$CTRL/work/studio_fast.json")
V131=$(verdict "$CTRL/work/dense_read.json")
if [ "$V132" = SKIP_ADOPTED ]; then export STUDIO_SKIP_EMPTY=1; else export STUDIO_SKIP_EMPTY=0; fi
if [ "$V131" = DENSE_READS_WORSE ]; then unset FL_DENSIFY; else export FL_DENSIFY=2; fi
echo "CONTROLS finding_132=$V132 finding_131=$V131 -> STUDIO_SKIP_EMPTY=$STUDIO_SKIP_EMPTY FL_DENSIFY=${FL_DENSIFY:-unset} $(date -Is)"
exec "$@"
