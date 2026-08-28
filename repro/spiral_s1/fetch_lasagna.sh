#!/usr/bin/env bash
# Fetch the s1 spiral-fitting dataset inputs. Resumable: wget -c, safe to re-run.
set -u
B=https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4
D="$(cd "$(dirname "$0")" && pwd)"
get() { wget -c -q --show-progress --progress=dot:giga -O "$D/$1" "$B/$1" 2>&1; }

mkdir -p "$D/lasagna_inputs/las_008_surf_sdt.ome.zarr.respool_g1" \
         "$D/lasagna_inputs/las_008_nx.ome.zarr.respool_g4_pair" \
         "$D/lasagna_inputs/las_008_grad_mag.ome.zarr.respool_g4" \
         "$D/outer_shell"

for f in umbilicus.json abs_winding.json relative_windings.json same_windings.json; do get "$f"; done
for f in meta.json x.tif y.tif z.tif; do get "outer_shell/$f"; done

P=lasagna_inputs/las_008_surf_sdt.ome.zarr.respool_g1
for f in meta.json brick_coords.npy table.npy channel_0.u8; do get "$P/$f"; done
P=lasagna_inputs/las_008_nx.ome.zarr.respool_g4_pair
for f in meta.json brick_coords.npy table.npy channel_0.u8 channel_1.u8; do get "$P/$f"; done
P=lasagna_inputs/las_008_grad_mag.ome.zarr.respool_g4
for f in meta.json brick_coords.npy table.npy channel_0.u8; do get "$P/$f"; done

echo "DONE $(date -Is)"
du -sh "$D"
