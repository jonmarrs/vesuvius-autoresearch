#!/usr/bin/env bash
# Watch villa upstream and say what any new commits do to the render path.
#
# It NOTIFIES, it never bumps. Taking a pin is a judgement call -- especially
# mid-study, where the question is not "is the new code good" but "does anything
# a running comparison depends on move underneath it". This gives you the facts
# to make that call and stops there.
#
# It also never touches the villa-spiral checkout. That tree is where renders and
# fits are built from, and fetching it mid-study would silently change what future
# work dirs contain, breaking comparability between arms of one comparison. Only
# the submodule is fetched here. See repro/spiral_render/setup_workdir.sh.
#
# Each new upstream tip is reported ONCE, with the render-path gate's verdict, so
# a long watch does not repeat itself.
#
# Usage:
#   watch_villa_upstream.sh [interval_seconds]     default 1800
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
VILLA="$REPO/villa"
INTERVAL="${1:-1800}"

[ -d "$VILLA/.git" ] || [ -f "$VILLA/.git" ] || {
  echo "no villa submodule at $VILLA" >&2; exit 2; }

echo "[watch] villa upstream, every ${INTERVAL}s, from $(git -C "$VILLA" rev-parse --short HEAD)"
echo "[watch] this notifies only; it never bumps the pin and never fetches villa-spiral"

last_reported=""
while true; do
  git -C "$VILLA" fetch origin --prune --quiet 2>/dev/null || {
    echo "[watch] fetch failed at $(date -Is), will retry"; sleep "$INTERVAL"; continue; }

  pin=$(git -C "$VILLA" rev-parse HEAD)
  up=$(git -C "$VILLA" rev-parse origin/main)
  behind=$(git -C "$VILLA" rev-list --count "$pin".."$up" 2>/dev/null || echo 0)

  if [ "$pin" != "$up" ] && [ "$up" != "$last_reported" ]; then
    echo
    echo "=========== VILLA UPSTREAM MOVED $(date -Is) ==========="
    echo "pin      $(git -C "$VILLA" log --oneline -1 "$pin")"
    echo "upstream $(git -C "$VILLA" log --oneline -1 "$up")"
    echo "behind   $behind commit(s):"
    git -C "$VILLA" log --oneline "$pin".."$up" | sed 's/^/    /'
    echo
    echo "--- render-path gate ---"
    python3 "$HERE/check_villa_render_path.py" "$pin" "$up" 2>&1 | sed 's/^/    /'
    echo "=========== end ==========="
    last_reported="$up"
  fi

  sleep "$INTERVAL"
done
