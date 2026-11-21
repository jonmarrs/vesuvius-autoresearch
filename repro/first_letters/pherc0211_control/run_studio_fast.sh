#!/usr/bin/env bash
# Finding 132: Studio with the winner's command, skipping the windows whose crop holds no CT, against the maps the
# winner's own inference.py made from the same inputs on this machine.
# Registration: docs/preregistration/2026-11-20_studio_skip_empty_windows.md. Each step only if the one before
# exited 0:
#   check    the weights, the winner's inference.py and PHerc. 211's input against their SHA-256 values
#   planes   Studio's input for PHerc. 0826's windings w062 and w065 from finding 125's renders (studio_e2e.py)
#   runs     studio_fast.py run on each input, the full loop then the skipping one, timed
#   compare  studio_fast.py compare, against finding 123's map (PHerc. 211) and finding 125's maps (PHerc. 0826)
# Studio's weights and outputs are CC BY-NC 4.0, and PHerc. 0826 is eligible: everything stays on this machine.
#
# usage: run_studio_fast.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"  # finding 118's C and WINNER
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
ENV=$C/work/studio_env
WEIGHTS=$C/inputs/studio/studio-softloss-20261023-ema.safetensors
CODE=$WINNER/v9/inference
PLANES_211=$C/inputs/studio/v9_model_input_planes16_uint8.npy
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
P_SHA=e7cdd509d74958a8cb95e9bfb0b1857610e457363edfe5329850b9b009ff8c22
R826=$FL_ROOT/pherc0826_band/work
BAND_WINDINGS=(w062 w065)  # the first two of finding 125's inspection order
OUT=$C/work/studio_fast
[ -e "$OUT" ] && { echo "$OUT exists: finding 132 runs once" >&2; exit 2; }
[ -x "$ENV/bin/python" ] || { echo "finding 123's Studio environment is missing" >&2; exit 2; }
for w in "${BAND_WINDINGS[@]}"; do
  [ -d "$R826/render_outer80/${w}_66.zarr" ] && [ -f "$R826/studio_outer80/maps/$w.npy" ] \
    || { echo "finding 125's $w is missing" >&2; exit 2; }
done
mkdir -p "$OUT/planes" "$OUT/maps" "$C/logs"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$C/logs/studio_fast_$name.log" 2>&1
  rc=$?
  control_gate "studio_fast_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

planes() {
  for w in "${BAND_WINDINGS[@]}"; do
    "$PYW" -I "$HERE/studio_e2e.py" planes "$R826/render_outer80/${w}_66.zarr" "$OUT/planes/$w.npy" || return 1
  done
}

one() {  # ARM NAME PLANES: one timed run of the winner's command, its record appended to runs.jsonl
  local flags=()
  [ "$1" = skip ] && flags=(--skip-empty)
  (cd "$CODE" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" -I "$HERE/studio_fast.py" run \
     --code "$CODE" --input "$3" --output "$OUT/maps/${1}_$2.npy" --checkpoint "$WEIGHTS" --batch-size 32 \
     --stride 64 --blend hann "${flags[@]}") > "$OUT/run_${1}_$2.json" || return 1
  printf '"%s_%s": %s\n' "$1" "$2" "$(cat "$OUT/run_${1}_$2.json")" >> "$OUT/runs.jsonl"
}

runs() {
  local w
  for arm in full skip; do one "$arm" pherc0211 "$PLANES_211" || return 1; done
  for w in "${BAND_WINDINGS[@]}"; do
    for arm in full skip; do one "$arm" "$w" "$OUT/planes/$w.npy" || return 1; done
  done
  { echo "{"; paste -sd, "$OUT/runs.jsonl"; echo "}"; } > "$OUT/runs.json"
}

nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 5 > "$OUT/gpu.csv" &
SMI=$!
trap 'kill "$SMI" 2>/dev/null' EXIT
step check bash -c "printf '%s  %s\n%s  %s\n%s  %s\n' '$W_SHA' '$WEIGHTS' '$CODE_SHA' '$CODE/inference.py' '$P_SHA' '$PLANES_211' | sha256sum -c"
step planes planes
step runs runs
PAIRS=(--pair full_pherc0211 "$OUT/maps/full_pherc0211.npy" "$C/work/studio_repro/ink.npy" "$PLANES_211"
       --pair skip_pherc0211 "$OUT/maps/skip_pherc0211.npy" "$C/work/studio_repro/ink.npy" "$PLANES_211")
for w in "${BAND_WINDINGS[@]}"; do
  for arm in full skip; do
    PAIRS+=(--pair "${arm}_$w" "$OUT/maps/${arm}_$w.npy" "$R826/studio_outer80/maps/$w.npy" "$OUT/planes/$w.npy")
  done
done
step compare "$PYW" -I "$HERE/studio_fast.py" compare "$C/work/studio_fast.json" "${PAIRS[@]}" \
  --seconds-json "$OUT/runs.json" --band-windings "${BAND_WINDINGS[@]}" --steps-ok yes
kill "$SMI" 2>/dev/null
peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
rm -f "$OUT"/planes/*.npy  # Studio's input, rebuilt from the renders when needed
grep '"verdict"' "$C/work/studio_fast.json"
