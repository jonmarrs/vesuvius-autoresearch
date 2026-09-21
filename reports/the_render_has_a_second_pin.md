# The render has a second pin, and none of today's provenance files recorded it

**2026-09-21.** Found when upstream #1828 changed `volume-cartographer/utils/src/zarr.cpp`.

## The gap

`setup_workdir.sh` records `VILLA_SHA` — the commit whose `spiral-fitting/`, `lasagna/` and
`vesuvius/src` are extracted into the work dir. That is the **Python stage**: `render_ink.py`, the
lasagna flatten, `get_ink_metrics.py`.

**`vc_render_tifxyz` is not in that tree.** The C++ sampler that actually reads voxels from the ink
volume is compiled into the `vc-render:local` Docker image from a *different* villa commit —
**`5479453a`**, 2026-08-30 — recorded only as `ARG VILLA_SHA` in the Dockerfile.

So every `VILLA_SHA` file written today says `be09a8503`, and none of them describes the binary
that samples the volume. Two pins, one recorded.

## Does it invalidate anything? No — and here is the check

Within the radial study every arm used the same image, so the comparison is internally consistent
regardless. The concern was whether #1828 — "fix double decoding of compressed Zarr shards" — means
the image's sampler reads *wrong values*.

The fix removes a redundant `decode_chunk_payload` after `extract_inner_chunk`, and it is
**shard-specific**. The ink volume is **zarr v2, unsharded**, at both pyramid levels (checked against
the live metadata). The buggy code path is never entered for this volume. The values are fine.

## The fix

`setup_workdir.sh` now writes a second file, `RENDER_IMAGE`, alongside `VILLA_SHA`: image name, image
id, build time, and the Dockerfile's `VILLA_SHA`. Backfilled into all six of today's work dirs, which
is safe because the image has not been rebuilt since 2026-08-30 and predates every arm.

**Rule:** a render's provenance is `(VILLA_SHA, RENDER_IMAGE)`, not `VILLA_SHA` alone. A future
image rebuild changes the sampler under every study without touching `VILLA_REF`, and until today
nothing would have noticed.

## Why the upstream monitor fired four times for this

It reports "hot path changed" against `VILLA_REF` — the Python-stage pin — so it flagged three
`lasagna/` commits (real, and already checked: the flatten is still stochastic) and then #1828, which
is not on the Python path at all. It sits on the *image* path, which the monitor does not know
exists. That is the same gap from the other side.
