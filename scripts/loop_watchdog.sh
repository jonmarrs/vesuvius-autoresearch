#!/bin/bash
# loop_watchdog.sh — keep the autoresearch loop alive.
#
# Installed in crontab (every few minutes + @reboot). The loop ends each
# day/night shift and exits, leaving the GPU idle until restarted; this bridges
# that gap and also recovers from crashes.
#
# Pause flag: if `.loop_paused` exists in the repo root, the watchdog does NOT
# restart the loop — so intentional stops (e.g. while editing train/model code)
# are respected. `start.sh` clears the flag. To pause: `touch .loop_paused`
# then stop the loop; to resume: `bash start.sh`.

export PATH="${HOME}/.local/bin:$PATH"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

# Respect an intentional pause.
if [ -f "$REPO/.loop_paused" ]; then
    exit 0
fi

# Already running? Nothing to do.
if python3 "$REPO/scripts/loop_control.py" status >/dev/null; then
    exit 0
else
    rc=$?
    [ "$rc" -eq 1 ] || exit "$rc"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') watchdog: loop not running, starting" >> "$REPO/watchdog.log"
bash "$REPO/start.sh" --watchdog >> "$REPO/watchdog.log" 2>&1
