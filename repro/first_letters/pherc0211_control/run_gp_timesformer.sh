#!/usr/bin/env bash
# Finding 122: the 2023 Grand Prize TimeSformer on finding 118's render of the winner's PHerc. 211 surface.
# Registration: docs/preregistration/2026-11-16_first_letters_0211_gp_timesformer.md. Runs once, each step only if
# the one before exited 0:
#   checksum   the canonical checkpoint (timesformer_wild15_20230702185753, from the authors' Drive in June)
#   audit      audit_pickle.py: the checkpoint's pickle imports only tensors, containers, AdamW and
#              CosineAnnealingLR, read without running it (torch's weights-only load cannot rebuild its defaultdict)
#   segments   gp_timesformer.py segments: the render in the script's layout, both layer orders
#   infer      villa's deprecated inference_timesformer.py (the 2023 winner's script, MIT), once per order, with a
#              stub wandb first on the path so that nothing it logs leaves the machine
#   compare    gp_timesformer.py compare
#
# villa's inference_timesformer.py loads with weights_only=False and is not modified. That load is safe only
# through this wrapper: copy $CK aside, then checksum, audit, and infer that copy. The SHA-256 pin
# 93f56e569e1f4c66b71112c41985b64445b5245ff1fb610e44f495c2a0aee36f is the exact $CK
# (villa/ink-detection/timesformer_weights.ckpt). A later swap of $CK is not the file that is loaded.
#
# usage: run_gp_timesformer.sh
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/env.sh"  # finding 118's C, WINNER, SEG, RENDER, MAPS
ROOT=$(cd "$HERE/../../.." && pwd)
PYW=${PYW:-$ROOT/.venv/bin/python}
# June's environment and weights are gitignored files in the main checkout's villa, not in a worktree's
MAIN=$(cd "$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)
GP_DIR=${GP_DIR:-$MAIN/villa/ink-detection}
PYGP=$GP_DIR/.venv-gp/bin/python
CK=$GP_DIR/timesformer_weights.ckpt
CK_SHA256=93f56e569e1f4c66b71112c41985b64445b5245ff1fb610e44f495c2a0aee36f
SCRIPT=$ROOT/villa/deprecated/ink-detection/inference_timesformer.py
OUT=$C/work/maps_gp
SEGS=$C/work/gp_segments
[ -e "$OUT" ] && { echo "$OUT exists: finding 122 runs once" >&2; exit 2; }
[ -f "$SCRIPT" ] && [ -x "$PYGP" ] && [ -s "$CK" ] || { echo "the Grand Prize script, environment or weights are missing" >&2; exit 2; }
[ -d "$RENDER/0" ] && [ -d "$C/work/maps_reader_v3/$SEG_NAME" ] || { echo "finding 118's render or 120's maps are missing" >&2; exit 2; }
mkdir -p "$C/logs" "$C/work/tmp"
# Checksum, audit, and infer this copy. $CK itself is never passed to the loader.
# The trap is set before the copy, so an interrupt during cp leaves no checkpoint-sized copy behind.
CK_DIR=$(mktemp -d "$C/work/tmp/gpck.XXXXXX") || exit 2
trap 'rm -rf "$CK_DIR"' EXIT
CK_COPY=$CK_DIR/timesformer_weights.ckpt
cp -- "$CK" "$CK_COPY"

step() {  # NAME COMMAND...: run, record the gate, stop on failure
  local name=$1 t0 rc
  shift
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$C/logs/gp_$name.log" 2>&1
  rc=$?
  control_gate "gp_$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

infer() {  # ORDER START_IDX
  local t
  # The copy is checksummed again at the load, so a swap after the audit step is refused.
  echo "$CK_SHA256  $CK_COPY" | sha256sum -c || return 1
  t=$(mktemp -d "$C/work/tmp/gp.XXXXXX") || return 1
  (cd "$t" && env -u PYTHONPATH PYTHONPATH="$HERE/gp_stub" PYTHONNOUSERSITE=1 WANDB_MODE=disabled \
     WANDB_SILENT=true HF_HUB_OFFLINE=1 "$PYGP" "$SCRIPT" --segment_path "$SEGS" --segment_id "$1" \
     --model_path "$CK_COPY" --out_path "$OUT" --start_idx "$2" --stride 32 --batch_size 64 --workers 2) || { rm -rf "$t"; return 1; }
  rm -rf "$t"
  [ -s "$OUT/${1}_prediction_rotated_0_layer_${2}.png" ] || { echo "no prediction for $1" >&2; return 1; }
}

# The sum and the path are arguments, not spliced into the command text, so a quote in $C cannot break it.
step checksum bash -c 'echo "$1  $2" | sha256sum -c' checksum "$CK_SHA256" "$CK_COPY"
step audit "$PYW" -I "$HERE/audit_pickle.py" "$CK_COPY" --allow torch.optim.adamw.AdamW \
  --allow torch.optim.lr_scheduler.CosineAnnealingLR --allow collections.defaultdict
step segments "$PYW" -I "$HERE/gp_timesformer.py" segments "$RENDER" "$SEGS"
mkdir -p "$OUT"
step infer_v9fwd infer v9fwd 18
step infer_v9rev infer v9rev 17
step compare "$PYW" -I "$HERE/gp_timesformer.py" compare "$C/work/gp_compare.json" \
  --mesh "$SEG" --maps "$MAPS" --render "$RENDER" \
  --studio "$WINNER/download/v9_studiosoft_probability_f32.tif" --studio-mask "$WINNER/v9/studiosoft-mask.png" \
  --winner-ct "$WINNER/download/v9_ct_layer.tif" --gp-maps "$OUT" --v3-maps "$C/work/maps_reader_v3/$SEG_NAME" \
  --image "$C/work/gp_compare_v9.png"
cat "$C/logs/gp_compare.log"
