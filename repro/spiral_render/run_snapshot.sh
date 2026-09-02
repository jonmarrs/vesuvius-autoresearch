#!/usr/bin/env bash
# Run a driver from a frozen copy of this directory, so editing the repo cannot
# corrupt a run in progress.
#
# Why this exists: bash reads a script incrementally by byte offset. Committing a
# documentation change to run_outer_arms.sh while a 90-minute render was executing
# it shifted the offsets under the live process, which resumed mid-token and died
# with `line 82: syntax error`. The render itself had already failed for an
# unrelated reason, but the driver could not even report it cleanly.
#
# A long study is exactly when you most want to write down what you are learning,
# so "just don't edit the file" is a rule that will be broken. Freezing a copy and
# running that removes the conflict instead of relying on discipline.
#
# Usage:
#   run_snapshot.sh <snapshot_root> <driver.sh> [args...]
#
# Example:
#   run_snapshot.sh /path/spiral_out run_outer_arms.sh /path/spiral_out 120 129 \
#     gap133s2=/path/meshes/fitted_gap133s2
#
# The snapshot directory is printed and kept: it is the exact code a run used, so
# it is also the record of what produced that arm.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

ROOT="${1:?usage: run_snapshot.sh <snapshot_root> <driver.sh> [args...]}"
DRIVER="${2:?which driver to run, e.g. run_outer_arms.sh}"
shift 2

[ -d "$ROOT" ] || { echo "no such snapshot root: $ROOT" >&2; exit 2; }
[ -f "$HERE/$DRIVER" ] || { echo "no such driver: $HERE/$DRIVER" >&2; exit 2; }

SNAP="$ROOT/_driver_snapshot_$(date +%Y%m%d_%H%M%S)"
cp -r "$HERE" "$SNAP" || { echo "snapshot copy failed" >&2; exit 2; }
chmod +x "$SNAP"/*.sh 2>/dev/null
[ -d "$SNAP/bin" ] && chmod +x "$SNAP"/bin/* 2>/dev/null

echo "[snapshot] running $DRIVER from $SNAP"
exec "$SNAP/$DRIVER" "$@"
