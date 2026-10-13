#!/usr/bin/env bash
# Copy each cycle's candidate (last_model.pt, written atomically by train.py)
# before the next cycle overwrites it. Read-only towards the loop.
#   scripts/snapshot_loop_candidates.sh <main checkout> <out dir> <max snapshots>
set -euo pipefail
main=$1 out=$2 max=$3
mkdir -p "$out"
last=$(stat -c %Y "$main/last_model.pt" 2>/dev/null || echo 0)
n=0
while [ "$n" -lt "$max" ]; do
    sleep 20
    now=$(stat -c %Y "$main/last_model.pt" 2>/dev/null || echo 0)
    if [ "$now" != "$last" ]; then
        sleep 5
        dest="$out/candidate_$(date -d "@$now" +%Y%m%d-%H%M%S).pt"
        cp -p "$main/last_model.pt" "$dest"
        echo "$(date -Is) $dest $(sha256sum "$dest" | cut -c1-16)"
        last=$now
        n=$((n + 1))
    fi
done
