#!/usr/bin/env bash
# The winning PHerc. 211 submission's files that finding 118 reads, from its public folder (CC BY-NC 4.0; the
# folder's LICENSE.md), checked against the SHA-256 recorded when the finding was registered. The folder is
# https://drive.google.com/drive/folders/1bvKolL_TIE3k5Ixi1qlOiAmofQ6r2ocH, linked from the organisers'
# announcement of 2026-11-15. Files already present are checked and kept.
#
# usage: fetch_winner.sh
set -u
. "$(dirname "$0")/env.sh"
mkdir -p "$WINNER/download"
fetch() {  # DRIVE_ID NAME SHA256
  local out=$WINNER/download/$2
  if [ ! -s "$out" ]; then
    curl -sfL -A "Mozilla/5.0" -o "$out.part" \
      "https://drive.usercontent.google.com/download?id=$1&export=download&confirm=t" || return 1
    mv "$out.part" "$out"
  fi
  echo "$3  $out" | sha256sum -c --quiet - || { echo "checksum of $2 differs" >&2; return 1; }
}
fetch 1aQhMxc3A5wYOBtHGy9fiJaGUyNwDzLmu v9_mesh.zip 819dcfb40451fab3fa58441d8265813c8ddbe2b5693bb076fce3eeefce05a5d9 || exit 1
fetch 1-Nlj0NUaQpVzcrVzBBf2TfcbUujh46s8 v9_studiosoft_probability_f32.tif \
  527c6fbbc5ac2d5a81d7cfb7ccc2925f2dc4b4d74627a0e7b08200d6874f071c || exit 1
fetch 1QSvag0VPvQr0X16fuE3O21llrFgTBGEV v9_ct_layer.tif \
  9c4bd4f56df9743d77e775e84be57d3cf9f3c2d6e75eb9dee614bb85b8f1e9c4 || exit 1
fetch 19Zg1qHenu_QRfu8YskesUS8_EXRt5my- LICENSE.md f94e46f8e6982c38fb497fe59d0b66178e9f10ca8ff708d49c9cb6e7d61aeb39 || exit 1
if [ ! -d "$WINNER/$SEG_NAME" ]; then
  mkdir -p "$WINNER/$SEG_NAME.part"
  unzip -q "$WINNER/download/v9_mesh.zip" -d "$WINNER/$SEG_NAME.part" || exit 1
  mv "$WINNER/$SEG_NAME.part/mesh" "$WINNER/$SEG_NAME" && rmdir "$WINNER/$SEG_NAME.part" || exit 1
fi
[ -f "$SEG/x.tif" ] && [ -f "$WINNER/$SEG_NAME/studiosoft-mask.png" ] || { echo "the mesh zip lacks its surface or mask" >&2; exit 1; }
echo "winner's files in $WINNER"
