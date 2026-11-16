#!/usr/bin/env bash
# List and download the chunks of the public arrays of the chosen scroll that the band Z_BEGIN-Z_END needs, each array
# into its own directory under R/inputs. Anonymous HTTPS listing and GET only; nothing is uploaded.
# The z chunks (env.sh: SURF_CHUNKS, CT_CHUNKS, LASAGNA_CHUNKS) cover the band +/- 64 slices, what run_sdt.sh reads;
# for the default band z 10250-11750:
#
#   surface prediction (m7, th 0.2)  level 1, 192-voxel chunks, z chunks 25-31   distance field (one chunk spare each side)
#   CT (masked)                      level 4 (all) and level 1, z chunks 39-46   CT-empty mask, checks
#   lasagna nx, ny, grad_mag         group 2, 32-voxel chunks, z chunks 79-92    fit
#   umbilicus                        the published scroll axis
set -u
. "$(dirname "$0")/../env.sh"
P=$R/plans; mkdir -p "$P" "$R/dataset"
PLAN="python3 -I $TOOLS/s3_plan.py"; FETCH="python3 -I $TOOLS/s3_fetch.py"
CTK=$SCROLL/volumes
rc=0
date
echo "z $Z_BEGIN-$Z_END: surface chunks $SURF_CHUNKS, CT $CT_CHUNKS, lasagna $LASAGNA_CHUNKS"
# shellcheck disable=SC2086  # each *_CHUNKS is two numbers
$PLAN "$BUCKET_SURF/$SURF_NAME/1" $SURF_CHUNKS "$P/surface_l1.tsv" || rc=1
$PLAN "$CTK/$CT_NAME/4" 0 99 "$P/ct_l4.tsv" || rc=1
# shellcheck disable=SC2086
$PLAN "$CTK/$CT_NAME/1" $CT_CHUNKS "$P/ct_l1.tsv" || rc=1
# shellcheck disable=SC2086
for a in nx ny grad_mag; do $PLAN "$LASAGNA/${SCROLL}_$a.ome.zarr/2" $LASAGNA_CHUNKS "$P/lasagna_$a.tsv" || rc=1; done
$FETCH "$BUCKET_SURF/" "$R/inputs/surface" "$P/surface_l1.tsv" --meta "$BUCKET_SURF/$SURF_NAME/.zattrs" \
  "$BUCKET_SURF/$SURF_NAME/.zgroup" "$BUCKET_SURF/$SURF_NAME/metadata.json" "$BUCKET_SURF/$SURF_NAME/1/.zarray" || rc=1
$FETCH "$CTK/" "$R/inputs/ct" "$P/ct_l4.tsv" "$P/ct_l1.tsv" --meta "$CTK/$CT_NAME/.zattrs" "$CTK/$CT_NAME/.zgroup" \
  "$CTK/$CT_NAME/1/.zarray" "$CTK/$CT_NAME/4/.zarray" || rc=1
m=()
for a in nx ny grad_mag; do
  m+=("$LASAGNA/${SCROLL}_$a.ome.zarr/.zattrs" "$LASAGNA/${SCROLL}_$a.ome.zarr/.zgroup" "$LASAGNA/${SCROLL}_$a.ome.zarr/2/.zarray")
done
$FETCH "$LASAGNA/" "$R/inputs/lasagna" "$P/lasagna_nx.tsv" "$P/lasagna_ny.tsv" "$P/lasagna_grad_mag.tsv" \
  --meta "$LASAGNA/$SCROLL.lasagna.json" "${m[@]}" || rc=1
curl -fsS -o "$R/dataset/umbilicus.json" "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/$UMBILICUS_KEY" || rc=1
date
echo "VOLUMES_EXIT $rc"
exit $rc
