#!/usr/bin/env bash
# Fetch all six PHerc.1667 ablation checkpoints. 318 MB each, ~1.9 GB total.
#
# DEST is where it0..it5 go (default: beside this script, which .gitignore covers). REVISION is the
# Hugging Face revision (default main, which is not pinned). The modelling code runs with
# trust_remote_code, so each member's files are hashed into it$i/SHA256SUMS the first time they are
# all present, and checked against it on every later run: a changed upstream file is reported and
# the run exits non-zero instead of using it.
set -u
D="${DEST:-$(cd "$(dirname "$0")" && pwd)}"
REVISION="${REVISION:-main}"
FILES="config.json configuration_inkdetection.py modeling_inkdetection.py model.safetensors"
status=0
for i in 0 1 2 3 4 5; do
  o="$D/it$i"; mkdir -p "$o"
  for f in $FILES; do
    [ -s "$o/$f" ] && continue
    curl -sfL --retry 3 -o "$o/$f" \
      "https://huggingface.co/scrollprize/PHerc.1667-iteration-$i/resolve/$REVISION/$f" \
      || { rm -f "$o/$f"; echo "MISS it$i/$f"; status=1; }
  done
  if [ -s "$o/SHA256SUMS" ]; then
    ( cd "$o" && sha256sum --quiet -c SHA256SUMS ) \
      || { echo "CHANGED it$i: its files differ from it$i/SHA256SUMS"; status=1; }
  elif ( cd "$o" && for f in $FILES; do [ -s "$f" ] || exit 1; done ); then
    ( cd "$o" && sha256sum $FILES > SHA256SUMS ) && echo "recorded it$i/SHA256SUMS"
  fi
  echo "it$i: $(du -sh "$o" | cut -f1)"
done
echo "DONE $(date -Is)"
exit $status
