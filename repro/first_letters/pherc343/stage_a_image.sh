#!/usr/bin/env bash
# Kill test stage A, CPU part: merge the plain/padded d = +1 maps as the repo does, then build the
# submission image twice with the repo's make_submission_image.py:
#   image_pubstats  normalisation taken from the published sidecar (the full 31-depth pooled values)
#   image_ownstats  no --ink-stats: statistics from these four d = +1 maps only (what one has
#                   without the 6-hour depth sweep)
set -euo pipefail
B=/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_repro
N=concat_w047-w048_R5B2_z9500-11000
R=$B/src/repo; S=$R/ink/scripts; W=$B/work; PY="$B/venv/bin/python -I"
$PY "$S/merge_tile_phase.py" --plain "$W/maps_plain" --plain-name "${N}_66" \
    --padded "$W/maps_padded" --padded-name "${N}_66_padded" \
    --node-source "$W/mesh/${N}_node_source.npz" --out "$W/maps" --out-name "$N"
mkdir -p "$W/images"
$PY "$B/scripts/stats_from_sidecar.py" "$R/outputs/$N.json" "${N}_66.zarr" "$W/images/${N}__stats.json"
(cd "$W/mesh" && sha256sum $N.tifxyz/x.tif $N.tifxyz/y.tif $N.tifxyz/z.tif $N.tifxyz/meta.json) > "$W/mesh_sums"
M=$W/maps
for V in pubstats ownstats; do
  EXTRA=(); [ "$V" = pubstats ] && EXTRA=(--ink-stats "$W/images/${N}__stats.json")
  $PY "$S/make_submission_image.py" --mesh "$W/mesh/$N.tifxyz" --umbilicus "$R/inputs/umbilicus_PHerc0343.json" \
      --ct "$W/${N}_66.zarr" --overlay-style dimmed-ct --caption compact --geometry-sums "$W/mesh_sums" \
      --area 380,105,6021,2560 --max-cm2 12 --ct-layer d+1 \
      --ink "$M/${N}__dnative__L66s26_reverse.tif" "$M/${N}__hecate__L66zc33.50_reverse.png" \
            "$M/${N}__hybrid_3d2d-seed42__L66s26_reverse.tif" "$M/${N}__hybrid_3d2d-seed43__L66s26_reverse.tif" \
      --ensemble "${EXTRA[@]}" \
      --rows "$R/inputs/${N}_rows.json" --letters "$R/inputs/${N}_letter_boxes.json" --letter-markers off \
      --sizes-csv "$W/image_$V/${N}_letter_sizes.csv" --out-dir "$W/image_$V" --force
done
sha256sum "$W"/image_*/$N.png "$R/outputs/$N.png" "$M"/*_reverse.*
echo IMAGE_DONE
