#!/usr/bin/env bash
# Download the three published PHerc. 0841 segments' meshes, ink images and labels, and the transform
# between the two scans (anonymous HTTPS listing and GET; nothing is uploaded). The 1.7 GB surface volumes
# on the 2.4 um scan and the meshes' intermediate files are not needed and are skipped.
set -u
. "$(dirname "$0")/env.sh"
mkdir -p "$R/published/transform" && cd "$R/published" || exit 2
rc=0
for s in $DEVELOPMENT $HELD_OUT; do
  curl -fsS -m 60 "$BUCKET/?list-type=2&prefix=PHerc0841/segments/$s/&max-keys=1000" \
    | grep -o '<Key>[^<]*</Key>' | sed 's/<[^>]*>//g' | grep -v "surface-volumes/\|mesh/intermediate/" > "keys_$s.txt" || rc=1
  while read -r k; do
    f=${k#PHerc0841/segments/}
    mkdir -p "$(dirname "$f")"
    [ -s "$f" ] || curl -fsS -R -m 300 -o "$f" "$BUCKET/$k" || rc=1
  done < "keys_$s.txt"
done
T=PHerc0841/transforms/20260319124803-to-20250821151531-r1
curl -fsS -m 60 -o transform/transform.json "$BUCKET/$T/fit/transform.json" || rc=1
curl -fsS -m 60 -o transform/provenance.json "$BUCKET/$T/provenance.json" || rc=1
echo "FETCH_EXIT $rc"
exit $rc
