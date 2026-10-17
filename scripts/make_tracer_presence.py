"""docs/preregistration/2026-10-16_neural_fiber_tracer_entrant.md -- the presence level villa's neural fiber tracer
seeds from, made from fiber_hz_vt's fiber probability.

villa's tracer (vesuvius.neural_tracing.tracers.fibers.tracing.volume, --presence) wants a uint8 presence array on
its trace grid. On a cube read at its own 7.91 um (--ct-level 0 --ct-grid-scale 1 --grid-scale 2) that grid is 2x
coarser than the CT. Each presence voxel here is round(255 x the mean probability of its 2x2x2 CT block).

The tracer parses the level directory's name as an integer and looks beside it for the next (coarser) level, which it
uses only to weigh tiles for progress. The level is written as OUT/1 (one level above the CT) with no OUT/2.

Usage: .venv/bin/python scripts/make_tracer_presence.py PROB.npy OUT.zarr    (writes OUT.zarr/1)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

FACTOR = 2
LEVEL = "1"
SLAB = 64  # CT slices per pass, to bound memory on 512^3 cubes


def presence_level(prob: np.ndarray, factor: int = FACTOR) -> np.ndarray:
    """(Z, Y, X) probabilities in [0, 1] -> (Z/f, Y/f, X/f) uint8 block means scaled to 0-255."""
    if prob.ndim != 3 or any(s % factor for s in prob.shape):
        raise ValueError(f"shape {prob.shape} is not a 3-D multiple of {factor}")
    z, y, x = (s // factor for s in prob.shape)
    out = np.empty((z, y, x), dtype=np.uint8)
    step = max(SLAB // factor, 1)
    for k in range(0, z, step):
        block = np.asarray(prob[k * factor : (k + step) * factor], dtype=np.float64)
        if not np.isfinite(block).all() or block.min() < 0 or block.max() > 1:
            raise ValueError("probabilities must be finite and in [0, 1]")
        n = block.shape[0] // factor
        means = block.reshape(n, factor, y, factor, x, factor).mean(axis=(1, 3, 5))
        out[k : k + n] = np.rint(means * 255)
    return out


def write_presence(prob_path: Path, out: Path) -> Path:
    """Write OUT/1, built beside OUT and renamed into place.

    The chain skips any cube whose presence level exists, and the identity check cannot see its content, so a write
    killed partway must not leave OUT: its unwritten chunks would read as zero presence, and fewer seeds.
    """
    import shutil

    import zarr

    if out.exists():
        raise FileExistsError(out)
    level = presence_level(np.load(prob_path, mmap_mode="r"))
    partial = out.with_name(out.name + ".partial")
    shutil.rmtree(partial, ignore_errors=True)  # left by a write that was killed
    array = zarr.open(
        str(partial / LEVEL),
        mode="w-",
        shape=level.shape,
        chunks=(64, 64, 64),
        dtype="u1",
    )
    array[...] = level
    partial.rename(out)
    return out / LEVEL


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prob", type=Path)
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    print(write_presence(args.prob, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
