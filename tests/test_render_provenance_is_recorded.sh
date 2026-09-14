#!/usr/bin/env bash
# Not a pytest: setup_workdir.sh is bash, and the property under test is that it
# RECORDS which villa commit a work dir was built from.
#
# Two incidents motivate it. On 2026-09-11 a submodule bump moved origin/main
# mid-corpus and split the arms across two render versions; on 2026-09-14 a
# background monitor fetched and moved it again mid-study. Both were invisible
# until someone reconstructed render order from file mtimes. A work dir that
# states its own provenance makes that a lookup instead of an investigation.
set -uo pipefail
R="$(cd "$(dirname "$0")/.." && pwd)"
S="$R/repro/spiral_render/setup_workdir.sh"
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }

echo "render provenance"
check "resolves a ref to a SHA before archiving" \
      'grep -q "VILLA_SHA=\"\$(git -C \"\$VILLA\" rev-parse" "$S"'
check "archives the resolved SHA, not a moving ref" \
      'grep -q "git -C \"\$VILLA\" archive \"\$VILLA_SHA\"" "$S"'
check "does not archive origin/main directly any more" \
      '! grep -q "archive origin/main" "$S"'
check "writes VILLA_SHA into the work dir" \
      'grep -q "> \"\$W/VILLA_SHA\"" "$S"'
check "the ref is overridable for a multi-arm study" \
      'grep -q "VILLA_REF=\"\${VILLA_REF:-" "$S"'
check "records why the comment alone was not enough" \
      'grep -q "BACKGROUND MONITOR" "$S"'
check "script still parses" 'bash -n "$S"'
[ "$fail" -eq 0 ] && echo "PASS" || echo "FAIL"
exit "$fail"
