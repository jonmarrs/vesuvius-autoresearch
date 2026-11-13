# Sourced by the PHerc. 0841 surface-control scripts. Everything large lives outside the repo, under R.
#   R  run directory of this control (the published segments, renders, maps, logs)
#   B  run directory of the PHerc. 343 kill test (the cloned recipe, checkpoints, ink environment)
#   M  run directory of the PHerc. 343 mesh step (the Python environment the analysis runs in)
R=${FL0841_DIR:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc0841_control}
B=${FL343_REPRO_DIR:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_repro}
M=${FL343_MESH_DIR:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_mesh}
PY=$M/venv_spiral/bin/python
RECIPE=$B/src/repo
BUCKET=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com
CT_URL=$BUCKET/PHerc0841/volumes/20250821151531-9.366um-1.2m-113keV-masked.zarr
RENDER_IMG=vc-render:sampler-75c79ac5f
RENDER_SHA=75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3
DEVELOPMENT=20260220213127-w00
HELD_OUT="20260220214732-auto_grown_20260220144552896 20260221022814-auto_grown_20260220174252405"
D_MIN=-8
D_MAX=8
mkdir -p "$R/work" "$R/logs"

# The published mesh of a segment on the 9.366 um scan, and the short name its render and maps carry.
segment_mesh() { echo "$R/published/$1/mesh/${1%%-*}-on-20250821151531-9.366um.tifxyz"; }
segment_name() { echo "s${1%%-*}"; }

# Record a step's exit code: R/work/gate/STEP.json
gate() {  # NAME EXIT SECONDS [EXTRA_JSON_FIELDS]
  mkdir -p "$R/work/gate"
  printf '{"exit": %s, "seconds": %s%s}\n' "$2" "$3" "${4:+, $4}" > "$R/work/gate/$1.json"
}
