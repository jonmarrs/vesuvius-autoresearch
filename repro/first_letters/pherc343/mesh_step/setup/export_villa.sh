#!/usr/bin/env bash
# Export villa's volume-cartographer Python sources at the pinned commit into R/villa_src (with the one
# module of vesuvius/src the spiral scripts import, vc3d_fiber_format, where they look for it) and apply the
# recipe's one-line patch there (fit_spiral.py: the shell becomes optional). The villa checkout itself is
# not touched.
set -euo pipefail
. "$(dirname "$0")/../env.sh"
[ "$(git -C "$V" rev-parse HEAD)" = "$VILLA_SHA" ] || { echo "$V is not at villa $VILLA_SHA" >&2; exit 2; }
[ -e "$R/villa_src" ] && { echo "$R/villa_src exists" >&2; exit 2; }
mkdir -p "$R/villa_src"
git -C "$V" archive "$VILLA_SHA" volume-cartographer/LICENSE volume-cartographer/README.md \
  volume-cartographer/pyproject.toml volume-cartographer/uv.lock volume-cartographer/python \
  volume-cartographer/scripts vesuvius/src/vc3d_fiber_format | tar -x -C "$R/villa_src"
( cd "$R/villa_src" && patch -p1 < "$RECIPE/mesh/fit_spiral_shell_optional.patch" )
