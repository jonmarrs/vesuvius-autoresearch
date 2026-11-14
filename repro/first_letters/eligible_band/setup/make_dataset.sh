#!/usr/bin/env bash
# Write the dataset description villa's fit_spiral reads for the chosen scroll. The tracks and the published scroll
# axis are already under R/dataset (setup/fetch_tracks.sh, setup/fetch_volumes.sh).
# The winding direction comes from env.sh.
set -euo pipefail
. "$(dirname "$0")/../env.sh"
[ -s "$R/dataset/umbilicus.json" ] || { echo "no umbilicus under $R/dataset" >&2; exit 2; }
[ -s "$R/dataset/tracks/$TRACKS_STEM.dbm" ] || { echo "no tracks under $R/dataset/tracks" >&2; exit 2; }
cat > "$R/dataset/spiral-scroll.json" <<JSON
{
  "schema_version": 1,
  "name": "$SCROLL",
  "voxel_size_um": $VOXEL_UM,
  "spiral_outward_sense": "$SENSE",
  "normal_zarr_group": "2",
  "surf_sdt_zarr_group": "1",
  "lasagna_scale": 4,
  "paths": {
    "tracks_dbm": "tracks/$TRACKS_STEM.dbm",
    "normal_x": "$R/inputs/lasagna/${SCROLL}_nx.ome.zarr",
    "normal_y": "$R/inputs/lasagna/${SCROLL}_ny.ome.zarr",
    "gradient_magnitude": "$R/inputs/lasagna/${SCROLL}_grad_mag.ome.zarr",
    "surf_sdt": "$SDT"
  }
}
JSON
echo "wrote $R/dataset/spiral-scroll.json (sense $SENSE)"
