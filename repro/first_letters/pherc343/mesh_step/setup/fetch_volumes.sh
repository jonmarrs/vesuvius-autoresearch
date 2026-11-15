#!/usr/bin/env bash
# List and download the chunks of the public PHerc. 343 arrays that the band z 9500-11000 needs, each array
# into its own directory under R/inputs. Anonymous HTTPS listing and GET only; nothing is uploaded.
#
#   surface prediction (m7, th 0.2)  level 1, 192-voxel chunks, z chunks 23-29   distance field
#   CT (masked)                      level 4 (all) and level 1, z chunks 36-43   CT-empty mask, checks
#   lasagna nx, ny, grad_mag         group 2, 32-voxel chunks, z chunks 73-86    fit
#
# The level-0 surface chunks the snap needs depend on the chosen windings; snap_chunks.py fetches those.
set -u
. "$(dirname "$0")/../env.sh"
HERE=$(cd "$(dirname "$0")/.." && pwd)
P=$R/plans; mkdir -p "$P"
PLAN="python3 -I $HERE/s3_plan.py"; FETCH="python3 -I $HERE/s3_fetch.py"
CTK=PHerc0343/volumes
CN=$(basename "$CT")
LAS=PHerc0343/representations/predictions/lasagna/20250521140437-lasagna-20260419180421
rc=0
date
$PLAN "$BUCKET_SURF/$SURF_NAME/1" 23 29 "$P/surface_l1.tsv" || rc=1
$PLAN "$CTK/$CN/4" 0 99 "$P/ct_l4.tsv" || rc=1
$PLAN "$CTK/$CN/1" 36 43 "$P/ct_l1.tsv" || rc=1
for a in nx ny grad_mag; do $PLAN "$LAS/PHerc0343_$a.ome.zarr/2" 73 86 "$P/lasagna_$a.tsv" || rc=1; done
$FETCH "$BUCKET_SURF/" "$R/inputs/surface" "$P/surface_l1.tsv" --meta "$BUCKET_SURF/$SURF_NAME/.zattrs" \
  "$BUCKET_SURF/$SURF_NAME/.zgroup" "$BUCKET_SURF/$SURF_NAME/metadata.json" "$BUCKET_SURF/$SURF_NAME/1/.zarray" || rc=1
$FETCH "$CTK/" "$R/inputs/ct" "$P/ct_l4.tsv" "$P/ct_l1.tsv" --meta "$CTK/$CN/.zattrs" "$CTK/$CN/.zgroup" \
  "$CTK/$CN/1/.zarray" "$CTK/$CN/4/.zarray" || rc=1
m=()
for a in nx ny grad_mag; do
  m+=("$LAS/PHerc0343_$a.ome.zarr/.zattrs" "$LAS/PHerc0343_$a.ome.zarr/.zgroup" "$LAS/PHerc0343_$a.ome.zarr/2/.zarray")
done
$FETCH "$LAS/" "$R/inputs/lasagna" "$P/lasagna_nx.tsv" "$P/lasagna_ny.tsv" "$P/lasagna_grad_mag.tsv" \
  --meta "$LAS/PHerc0343.lasagna.json" "${m[@]}" || rc=1
date
echo "VOLUMES_EXIT $rc"
exit $rc
