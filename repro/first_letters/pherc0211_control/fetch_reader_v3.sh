#!/usr/bin/env bash
# Finding 120: the released Reader V3 checkpoint (MIT; github.com/DomRusso2/reader-v3, weights on Hugging Face
# domenicor046/reader-v3), pinned to the revision read on 2026-11-16 and checked against its LFS SHA-256. Then
# check_checkpoint.py loads it with torch's weights-only unpickler: villa's loader uses weights_only=False, so a
# checkpoint is only handed to villa after it has been shown to hold nothing but tensors and plain values.
#
# usage: fetch_reader_v3.sh
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
REVISION=aee1d64bced4eb35546348f3d276b9e2a0b99c46
SHA256=ea405417450abd8ace1b8ff79ebce3adb646c5e48ab95da46844d77efe984d8a
DIR=$C/inputs/reader_v3
OUT=$DIR/reader-v3.pth
mkdir -p "$DIR"
if [ ! -s "$OUT" ]; then
  curl -sfL -o "$OUT.part" "https://huggingface.co/domenicor046/reader-v3/resolve/$REVISION/reader-v3.pth" || exit 1
  mv "$OUT.part" "$OUT"
fi
echo "$SHA256  $OUT" | sha256sum -c --quiet - || { echo "checksum of reader-v3.pth differs" >&2; exit 1; }
env -u PYTHONPATH PYTHONNOUSERSITE=1 "$B/venv/bin/python" -I "$HERE/check_checkpoint.py" "$OUT"
