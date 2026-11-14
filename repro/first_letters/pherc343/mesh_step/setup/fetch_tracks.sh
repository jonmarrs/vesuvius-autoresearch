#!/usr/bin/env bash
# Download the public PHerc. 343 spiral tracks (anonymous HTTPS GET; nothing is uploaded).
# Usage: fetch_tracks.sh DEST_DIR      Resumable: rerun to continue partial files.
set -euo pipefail
DEST=$1
BASE=https://dl.ash2txt.org/datasets/spiral_datasets/PHerc0343/20250521140437/tracks
STEM=PHerc0343_20250521140437_surface_m7_L0_th0.2
mkdir -p "$DEST/$STEM.dbm.vctracks"
echo "FETCH_START $(date -Is)"
get() { curl -fsS -R -C - --retry 8 --retry-delay 20 --retry-all-errors -o "$DEST/$1" "$BASE/$1"; echo "got $1 $(stat -c %s "$DEST/$1")"; }
get "$STEM.extract.json"
for f in header.bin metadata.json family_codes.i8 arclengths.f64 offsets.i64 source_ids.u64 tortuosities.f64 z_bounds.i32 coordinates.i32; do
  get "$STEM.dbm.vctracks/$f"
done
get "$STEM.dbm.crossings.npz"
get "$STEM.dbm"
# villa 0fb38c45 accepts the packed store and the crossing cache only if the DBM's size and mtime IN
# NANOSECONDS equal the ones recorded when they were built. HTTP's Last-Modified carries whole seconds, so a
# download never matches: the fit then ignores both, unpickles the 9 GiB DBM in Python (1 min 41 s here) and
# was killed for memory pressure on this host. Restore the recorded mtime. villa main validates by content
# digest instead (#2041).
NS=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_db_signature"][0][2])' \
  "$DEST/$STEM.dbm.vctracks/metadata.json")
touch -d "@${NS:0:${#NS}-9}.${NS: -9}" "$DEST/$STEM.dbm"
echo "set $STEM.dbm mtime to $NS ns"
echo "FETCH_EXIT 0 $(date -Is)"
