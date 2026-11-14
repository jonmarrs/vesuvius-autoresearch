# Sourced by the eligible-scroll band scripts. Everything large lives outside the repo, under R, and nothing
# made from these scrolls leaves this machine: they are prize-eligible.
#   R  run directory of this band (inputs, dataset, work, logs): FL_ROOT/<scroll>_band
#   B  run directory of the PHerc. 343 kill test (the cloned recipe, checkpoints, ink environment)
#   M  run directory of the PHerc. 343 mesh step (villa 0fb38c45 with the recipe's patch, its Python
#      environment and native build are used from it, unchanged)
FL_ROOT=${FL_ROOT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters}
B=${FL343_REPRO_DIR:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_repro}
M=${FL343_MESH_DIR:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_mesh}
V=${FL343_VILLA_DIR:-/home/jon/openclaw-workspace/Neo-VM/projects/villa-wt-ink-0fb38c45}
SPIRAL=$M/villa_src/volume-cartographer/scripts/spiral
PY=$M/venv_spiral/bin/python
RECIPE=$B/src/repo
TOOLS=$(cd "$(dirname "${BASH_SOURCE[0]}")/../pherc343/mesh_step" && pwd)
# The scroll is chosen with FL_SCROLL. Per scroll: the volume id, the published scroll axis, and the winding
# direction villa derives from the open-data catalog's orientation flags (z_direction_is_top_to_bottom !=
# left_handed_coordinates gives ACW, else CW; metadata.json read 2026-11-13). PHerc. 0125's z direction is
# null in the catalog, so its direction is unknown and it has no default here.
SCROLL=${FL_SCROLL:-PHerc0211}
case "$SCROLL" in
  PHerc0211) VOLUME_ID=20250821151803; UMBILICUS_STAMP=20260808112626; SENSE=ACW ;;
  PHerc0826) VOLUME_ID=20250821151701; UMBILICUS_STAMP=20260808113303; SENSE=ACW ;;
  PHerc0125) VOLUME_ID=20250821151825; UMBILICUS_STAMP=20260808111524
             SENSE=${FL_SENSE:?PHerc0125 has no published direction: set FL_SENSE} ;;
  *) echo "unknown scroll $SCROLL" >&2; return 2 2>/dev/null || exit 2 ;;
esac
VOXEL_UM=9.362
Z_BEGIN=${FL_Z_BEGIN:-10250}   # default: the middle 1,500 slices of the tracked range z 4500-17500
Z_END=${FL_Z_END:-11750}
R=$FL_ROOT/$(echo "$SCROLL" | tr "[:upper:]" "[:lower:]")_band
BUCKET_SURF=$SCROLL/representations/predictions/surfaces
SURF_NAME=$VOLUME_ID-surface-20260413222639-surface-m7-L0-th0.2.zarr
SURF=$R/inputs/surface/$SURF_NAME
CT_NAME=$VOLUME_ID-9.362um-1.2m-113keV-masked.zarr
CT=$R/inputs/ct/$CT_NAME
CT_URL=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/$SCROLL/volumes/$CT_NAME
LASAGNA=$SCROLL/representations/predictions/lasagna/$VOLUME_ID-lasagna-20260419180421
UMBILICUS_KEY=$SCROLL/representations/umbilicus/$VOLUME_ID-umbilicus-$UMBILICUS_STAMP.json
TRACKS_STEM=${SCROLL}_${VOLUME_ID}_surface_m7_L0_th0.2
SDT=$R/work/surf_sdt/${SCROLL}_surf_sdt.ome.zarr
RENDER_IMG=vc-render:sampler-75c79ac5f
RENDER_SHA=75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3
VILLA_SHA=0fb38c45b488e192566ea83ae36369cb6db92652
export PYTHONPATH=$M/native/build PYTHONNOUSERSITE=1
mkdir -p "$R/work" "$R/logs"

# Record a step's exit code: R/work/gate_ARM/STEP.json
gate() {  # ARM NAME EXIT SECONDS [EXTRA_JSON_FIELDS]
  mkdir -p "$R/work/gate_$1"
  printf '{"exit": %s, "seconds": %s%s}\n' "$3" "$4" "${5:+, $5}" > "$R/work/gate_$1/$2.json"
}

# The folder of raw windings a fit arm wrote: R/work/fit_ARM/<run>/meshes/<one folder>/wNNN.
fit_meshes() {
  local found=()
  for d in "$R/work/fit_$1"/*/meshes/*/; do
    case "$d" in *_spliced/) continue ;; esac
    [ -d "$d" ] && found+=("${d%/}")
  done
  [ "${#found[@]}" -eq 1 ] || { echo "expected one mesh folder under $R/work/fit_$1/*/meshes, found ${#found[@]}" >&2; return 1; }
  echo "${found[0]}"
}
