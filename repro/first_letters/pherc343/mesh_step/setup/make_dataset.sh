#!/usr/bin/env bash
# Write the dataset folder villa's fit_spiral reads: the scroll description, the recipe's scroll axis
# (copied from the cloned recipe, not kept in this repository) and the tracks fetched by fetch_tracks.sh.
set -euo pipefail
. "$(dirname "$0")/../env.sh"
mkdir -p "$R/dataset/tracks"
cp "$RECIPE/inputs/umbilicus_PHerc0343.json" "$R/dataset/umbilicus.json"
cat > "$R/dataset/spiral-scroll.json" <<JSON
{
  "schema_version": 1,
  "name": "PHerc0343",
  "voxel_size_um": 8.64,
  "spiral_outward_sense": "CW",
  "normal_zarr_group": "2",
  "surf_sdt_zarr_group": "1",
  "lasagna_scale": 4,
  "paths": {
    "tracks_dbm": "tracks/PHerc0343_20250521140437_surface_m7_L0_th0.2.dbm",
    "normal_x": "$R/inputs/lasagna/PHerc0343_nx.ome.zarr",
    "normal_y": "$R/inputs/lasagna/PHerc0343_ny.ome.zarr",
    "gradient_magnitude": "$R/inputs/lasagna/PHerc0343_grad_mag.ome.zarr",
    "surf_sdt": "$SDT"
  }
}
JSON
