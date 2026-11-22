# Sourced by the mesh-step scripts. Everything large lives outside the repo, under R.
#   R  run directory of this step (inputs, environment, work, logs)
#   B  run directory of the kill test (the cloned recipe, checkpoints, the published windings and maps)
#   V  a checkout of villa at 0fb38c45 (the lasagna flattener and vesuvius/src are used from it, unchanged)
R=${FL343_MESH_DIR:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_mesh}
B=${FL343_REPRO_DIR:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_repro}
V=${FL343_VILLA_DIR:-/home/jon/openclaw-workspace/Neo-VM/projects/villa-wt-ink-0fb38c45}
VILLA_SHA=0fb38c45b488e192566ea83ae36369cb6db92652
SPIRAL=$R/villa_src/volume-cartographer/scripts/spiral   # villa 0fb38c45, with the recipe's one-line patch
PY=$R/venv_spiral/bin/python
RECIPE=$B/src/repo
BUCKET_SURF=PHerc0343/representations/predictions/surfaces
SURF_NAME=20250521140437-surface-20260413222639-surface-m7-L0-th0.2.zarr
SURF=$R/inputs/surface/$SURF_NAME
CT=$R/inputs/ct/20250521140437-8.640um-1.2m-116keV-masked.zarr
CT_URL=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr
SDT=$R/work/surf_sdt/PHerc0343_surf_sdt.ome.zarr
SEGMENT=concat_w047-w048_R5B2_z9500-11000
PUBLISHED_W047=$RECIPE/outputs/w047_R5B2_z9500-11000.tifxyz
PUBLISHED_W048=$RECIPE/outputs/w048_R5B2_z9500-11000.tifxyz
RENDER_IMG=vc-render:sampler-75c79ac5f
RENDER_SHA=75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3
export PYTHONPATH=$R/native/build PYTHONNOUSERSITE=1
mkdir -p "$R/work" "$R/logs"

# The folder of raw windings a fit arm wrote. villa names the run folder itself (date, scroll, z range):
# R/work/fit_ARM/<run>/meshes/<one folder>/wNNN, with a wNNN_spliced twin beside each.
fit_meshes() {
  local found=()
  for d in "$R/work/fit_$1"/*/meshes/*/; do
    case "$d" in *_spliced/) continue ;; esac
    [ -d "$d" ] && found+=("${d%/}")
  done
  [ "${#found[@]}" -eq 1 ] || { echo "expected one mesh folder under $R/work/fit_$1/*/meshes, found ${#found[@]}" >&2; return 1; }
  echo "${found[0]}"
}

# Record a step's exit code for the gate: R/work/gate_ARM/STEP[_WINDING].json
gate() {  # ARM NAME EXIT SECONDS [EXTRA_JSON_FIELDS]
  mkdir -p "$R/work/gate_$1"
  printf '{"exit": %s, "seconds": %s%s}\n' "$3" "$4" "${5:+, $5}" > "$R/work/gate_$1/$2.json"
}
