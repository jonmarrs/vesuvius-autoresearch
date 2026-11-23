#!/usr/bin/env bash
# Fetch the PHerc. 306B team's glyph CNN (gA.pt, 2.6 MB, CC BY-NC 4.0) from their repository at the commit glyph.py
# names, and check it against glyph.py's sha256. An anonymous read of a public file; nothing is sent.
#
# usage: fetch_glyph.sh DEST_DIR
set -eu
DEST=${1:?usage: fetch_glyph.sh DEST_DIR}
COMMIT=feabff6c54f95bd8e52a90e0a7a76881ee67d4cc
SHA=36ae0d6d9fdaac9d8681af75ec9be17e9317f7f77aa9422ea8ff8d09dd6f19ad
mkdir -p "$DEST"
[ -f "$DEST/gA.pt" ] || curl -fsSL -o "$DEST/gA.pt.part" \
  "https://raw.githubusercontent.com/SirProdigle/pherc0306b-first-letters/$COMMIT/discovery/x_glyph/models/gA.pt"
[ -f "$DEST/gA.pt" ] || mv "$DEST/gA.pt.part" "$DEST/gA.pt"
echo "$SHA  $DEST/gA.pt" | sha256sum -c
