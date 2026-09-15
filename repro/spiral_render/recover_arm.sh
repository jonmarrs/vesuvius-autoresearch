#!/usr/bin/env bash
# Re-render and score an arm whose FIT succeeded but whose render was OOM-killed.
#
# 2026-09-14: curbase_s7's render was OOM-killed three times (28.2-28.7G anon-rss
# on a 31.3G box). The chain logged "[fail] curbase_s7 NOT scored after retries"
# and moved on, leaving triplet C incomplete. The fit was fine: 120 spliced mesh
# dirs, byte-for-byte as many as a successfully rendered arm. So recovery is a
# ~2h re-render, NOT a 5h refit -- run_arm_sequence.sh skips an arm that already
# has meshes/fitted_<tag>/ ("[skip] TAG already fitted").
#
# THE PRECHECK IS THE POINT. Re-running into an unchanged memory margin just
# spends two more hours reaching the same kill. reports/the_render_margin_is_800MB.md
# measured that margin at 0.8GB: 31.3G total, 2.1G held by desktop and agent
# processes, against a 28.5G render peak. This refuses to start unless there is
# real headroom, and says what to free when there is not.
#
#   VILLA_REF=<sha> ./recover_arm.sh <spiral_out> <first> <last> <tag> [tag...]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
ROOT="${1:?usage: recover_arm.sh <spiral_out> <first_winding> <last_winding> <tag>...}"
FIRST="${2:?}"; LAST="${3:?}"; shift 3
[ "$#" -gt 0 ] || { echo "no arms given" >&2; exit 2; }

NEED_GB="${NEED_GB:-30}"
avail=$(awk '/^MemAvailable/{printf "%.1f", $2/1048576}' /proc/meminfo)
echo "[precheck] MemAvailable ${avail}G, render peak needs about ${NEED_GB}G"

# Refuse while anything heavy is already running; the guard knows about the
# containerised renderer, which a venv-only match misses entirely.
if ! "$REPO/.venv/bin/python" "$REPO/scripts/guard_heavy_analysis.py" --fail-if-any >/dev/null 2>&1; then
  echo "[precheck] FAIL: a render or heavy job is already in flight. These are" >&2
  echo "           sequential by design -- two at once swaps the box into uselessness." >&2
  exit 1
fi

if awk -v a="$avail" -v n="$NEED_GB" 'BEGIN{exit !(a < n)}'; then
  echo "[precheck] FAIL: ${avail}G available, need ~${NEED_GB}G." >&2
  echo "           The margin has been 0.8GB; re-rendering now just buys another OOM." >&2
  echo "           Free memory first (the desktop apps hold ~2.1G of RSS), or add swap." >&2
  echo "           Override with NEED_GB=<n> only if you know why." >&2
  exit 1
fi

echo "[precheck] ok, proceeding"
exec "$HERE/run_arm_sequence.sh" "$ROOT" "$FIRST" "$LAST" "$@"
