#!/bin/bash
# Stop this checkout's loop and persist the pause for its watchdog.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$REPO/scripts/loop_control.py" stop --repo "$REPO"
