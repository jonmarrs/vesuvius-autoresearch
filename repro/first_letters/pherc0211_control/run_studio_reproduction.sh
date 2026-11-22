#!/usr/bin/env bash
# Finding 123: Studio (the reader that won PHerc. 211's First Letters prize) run here from the winner's supplied
# weights and 16-plane input, against the winner's map. Registration:
# docs/preregistration/2026-11-16_first_letters_0211_studio_reproduction.md. Each step only if the one before
# exited 0:
#   fetch     the weights from the code repository's release and the 16-plane input from the winner's public
#             folder, each checked against the SHA-256 in the winner's inference-record.json (anonymous reads)
#   env       the winner's pinned inference environment (requirements-inference-exact.txt + numpy and safetensors,
#             Python 3.11.16), built by uv in an isolated folder under C/work
#   infer     the winner's bundled inference.py (checked against the record's SHA-256) with the record's command
#   compare   studio_reproduce.py
# The weights and outputs are CC BY-NC 4.0 (the code is MIT); they stay on this machine.
#
# usage: run_studio_reproduction.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"  # finding 118's C, WINNER
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
V9=$WINNER/v9
IN=$C/inputs/studio
ENV=$C/work/studio_env
OUT=$C/work/studio_repro
WEIGHTS=$IN/studio-softloss-20261023-ema.safetensors
PLANES=$IN/v9_model_input_planes16_uint8.npy
W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90
P_SHA=e7cdd509d74958a8cb95e9bfb0b1857610e457363edfe5329850b9b009ff8c22
CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0
W_URL=https://github.com/priyankaranke/vesuvius-studio-multiscroll-cpt/releases/download/studio-softloss-20261023/studio-softloss-20261023-ema.safetensors
P_ID=1Vj74td-fosHQLacQFIJ-i41inF6j6DH2
[ -e "$OUT" ] && { echo "$OUT exists: finding 123 runs once" >&2; exit 2; }
[ -f "$V9/inference/inference.py" ] && [ -f "$V9/requirements-inference-exact.txt" ] || { echo "the winner's mesh folder is missing" >&2; exit 2; }
mkdir -p "$C/logs" "$IN"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$C/logs/studio_$name.log" 2>&1
  rc=$?
  control_gate "studio_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

fetch() {
  if [ ! -s "$WEIGHTS" ]; then curl -sfL -A "Mozilla/5.0" -o "$WEIGHTS.part" "$W_URL" && mv "$WEIGHTS.part" "$WEIGHTS" || return 1; fi
  if [ ! -s "$PLANES" ]; then
    curl -sfL -A "Mozilla/5.0" -o "$PLANES.part" \
      "https://drive.usercontent.google.com/download?id=$P_ID&export=download&confirm=t" && mv "$PLANES.part" "$PLANES" || return 1
  fi
  printf '%s  %s\n%s  %s\n%s  %s\n' "$W_SHA" "$WEIGHTS" "$P_SHA" "$PLANES" "$CODE_SHA" "$V9/inference/inference.py" | sha256sum -c
}

environment() {
  # the winner's helper bootstraps uv 0.13.6 when none is installed; this machine's uv (0.11.18) does not know
  # CPython 3.11.16, so the same bootstrap is used here, in its own folder (amendment 1 of the registration)
  local uvb=$C/work/studio_bootstrap/bin/uv
  if [ ! -x "$uvb" ]; then
    python3 -m venv "$C/work/studio_bootstrap" && "$C/work/studio_bootstrap/bin/python" -m pip install 'uv==0.13.6' || return 1
  fi
  "$uvb" python install 3.11.16 || return 1
  [ -x "$ENV/bin/python" ] || "$uvb" venv --python 3.11.16 "$ENV" || return 1
  "$uvb" pip install --python "$ENV/bin/python" --index-url https://pypi.org/simple -r "$V9/requirements-inference-exact.txt" || return 1
  "$uvb" pip install --python "$ENV/bin/python" 'numpy==2.4.6' 'safetensors==0.8.0' || return 1
  "$ENV/bin/python" -I -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.is_bf16_supported())"
}

infer() {
  local smi rc peak
  mkdir -p "$OUT"
  nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 2 > "$OUT/gpu.csv" &
  smi=$!
  (cd "$V9/inference" && env -u PYTHONPATH PYTHONNOUSERSITE=1 HF_HUB_OFFLINE=1 "$ENV/bin/python" inference.py \
     --input "$PLANES" --output "$OUT/ink.npy" --checkpoint "$WEIGHTS" --stride 64 --blend hann --batch-size 32)
  rc=$?
  kill "$smi" 2>/dev/null
  peak=$(cut -d, -f2 "$OUT/gpu.csv" | tr -dc '0-9\n' | sort -n | tail -1)
  echo "gpu_peak_mib_all_processes ${peak:-null}"
  printf '{"gpu_peak_mib_all_processes": %s}\n' "${peak:-null}" > "$OUT/gpu_peak.json"
  return $rc
}

step fetch fetch
step env environment
step infer infer
step compare "$PYW" -I "$HERE/studio_reproduce.py" "$C/work/studio_repro.json" "$OUT/ink.npy" \
  "$WINNER/download/v9_studiosoft_probability_f32.tif" "$V9/studiosoft-mask.png" --gate "$C/work/gate/studio_infer.json"
cat "$C/logs/studio_compare.log"
