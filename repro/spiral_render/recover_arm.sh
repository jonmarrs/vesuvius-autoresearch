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

# CAPACITY IS RAM PLUS FREE SWAP, not RAM alone. The first version of this check
# compared MemAvailable against 30G, which on a 31.3G box is never true once
# anything at all is running -- it would have refused forever. It also ignored the
# thing that actually decides the outcome: a render that can spill to swap survives
# the peak, and one that cannot is killed at it. curbase_s7 died three times with
# swap nearly full; s8 got through after swap went 8G -> 24G, its RSS FALLING from
# 26.0G to 24.8G as pages moved out.
# VILLA MUST BE SET HERE, and to the checkout the study actually used.
# setup_workdir.sh defaults VILLA to .../Neo-VM/villa-spiral, but the consensus
# chain exported the SUBMODULE instead, and the two are not interchangeable:
# villa-spiral does not contain be09a8503 at all. Left unset, a recovery passes
# this precheck and then dies ~30s later inside setup_workdir with "unknown
# revision" -- loud, but only after the operator believes it has started.
VILLA="${VILLA:-$REPO/villa}"
export VILLA
if [ -n "${VILLA_REF:-}" ]; then
  if ! git -C "$VILLA" rev-parse --verify "${VILLA_REF}^{commit}" >/dev/null 2>&1; then
    echo "[precheck] FAIL: VILLA_REF=$VILLA_REF does not resolve in $VILLA." >&2
    echo "           The arms being matched were rendered from a specific tree; a" >&2
    echo "           different checkout is not a substitute. Point VILLA at the one" >&2
    echo "           that has it." >&2
    exit 1
  fi
  export VILLA_REF
  echo "[precheck] villa $VILLA_REF resolves in ${VILLA##*/Neo-VM/}"
else
  echo "[precheck] WARNING: VILLA_REF unset; setup_workdir will follow a MOVING ref." >&2
  echo "           Arms rendered from different trees are not comparable. Pin it." >&2
fi

NEED_GB="${NEED_GB:-32}"          # 28.5G measured peak plus headroom
ram=$(awk '/^MemAvailable/{printf "%.1f", $2/1048576}' /proc/meminfo)
swp=$(awk '/^SwapFree/{printf "%.1f", $2/1048576}' /proc/meminfo)
avail=$(awk -v a="$ram" -v b="$swp" 'BEGIN{printf "%.1f", a+b}')
echo "[precheck] capacity ${avail}G = ${ram}G RAM + ${swp}G free swap; peak needs about ${NEED_GB}G"

# Refuse while anything heavy is already running; the guard knows about the
# containerised renderer, which a venv-only match misses entirely.
if ! "$REPO/.venv/bin/python" "$REPO/scripts/guard_heavy_analysis.py" --fail-if-any >/dev/null 2>&1; then
  echo "[precheck] FAIL: a render or heavy job is already in flight. These are" >&2
  echo "           sequential by design -- two at once swaps the box into uselessness." >&2
  exit 1
fi

if awk -v a="$avail" -v n="$NEED_GB" 'BEGIN{exit !(a < n)}'; then
  echo "[precheck] FAIL: ${avail}G capacity (${ram}G RAM + ${swp}G swap), need ~${NEED_GB}G." >&2
  echo "           A render that cannot spill is killed at its peak: that is how" >&2
  echo "           curbase_s7 was lost three times. Free RAM or add swap first." >&2
  echo "           Override with NEED_GB=<n> only if you know why." >&2
  exit 1
fi

echo "[precheck] ok, proceeding"
exec "$HERE/run_arm_sequence.sh" "$ROOT" "$FIRST" "$LAST" "$@"
