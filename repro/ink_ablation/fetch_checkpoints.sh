#!/usr/bin/env bash
# Fetch all six PHerc.1667 ablation checkpoints. 318 MB each, ~1.9 GB total.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
for i in 0 1 2 3 4 5; do
  o="$D/it$i"; mkdir -p "$o"
  for f in config.json configuration_inkdetection.py modeling_inkdetection.py model.safetensors; do
    [ -s "$o/$f" ] && continue
    curl -sfL --retry 3 -o "$o/$f" \
      "https://huggingface.co/scrollprize/PHerc.1667-iteration-$i/resolve/main/$f" \
      || { rm -f "$o/$f"; echo "MISS it$i/$f"; }
  done
  echo "it$i: $(du -sh $o | cut -f1)"
done
echo "DONE $(date -Is)"
