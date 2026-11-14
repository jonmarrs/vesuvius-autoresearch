#!/usr/bin/env bash
# Download the chosen scroll's public spiral tracks (anonymous HTTPS GET; nothing is uploaded) into R/dataset/tracks
# and restore the modification time villa 0fb38c45 checks (see ../../pherc343/mesh_step/setup/fetch_tracks.sh).
# Resumable: rerun to continue partial files.
set -euo pipefail
. "$(dirname "$0")/../env.sh"
DEST=$R/dataset/tracks
BASE=https://dl.ash2txt.org/datasets/spiral_datasets/$SCROLL/$VOLUME_ID/tracks
STEM=$TRACKS_STEM
mkdir -p "$DEST/$STEM.dbm.vctracks"
echo "FETCH_START $(date -Is)"
get() { curl -fsS -R -C - --retry 8 --retry-delay 20 --retry-all-errors -o "$DEST/$1" "$BASE/$1"; echo "got $1 $(stat -c %s "$DEST/$1")"; }
get "$STEM.extract.json"
for f in header.bin metadata.json family_codes.i8 arclengths.f64 offsets.i64 source_ids.u64 tortuosities.f64 z_bounds.i32 coordinates.i32; do
  get "$STEM.dbm.vctracks/$f"
done
get "$STEM.dbm.crossings.npz"
get "$STEM.dbm"
NS=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_db_signature"][0][2])' \
  "$DEST/$STEM.dbm.vctracks/metadata.json")
touch -d "@${NS:0:${#NS}-9}.${NS: -9}" "$DEST/$STEM.dbm"
echo "set $STEM.dbm mtime to $NS ns"
echo "FETCH_EXIT 0 $(date -Is)"
