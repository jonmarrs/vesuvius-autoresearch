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
    """Write OUT/1, built in a directory of its own beside OUT and renamed into place.

    The chain reuses the presence level of any cube whose level exists, and the identity check cannot see its
    content. So a write killed partway must not leave OUT: its unwritten chunks would read as zero presence, and
    fewer seeds. Each writer builds in its own directory, so two writers on one cube cannot clear each other's work;
    the second to finish finds OUT written and refuses.
    """
    import shutil
    import tempfile

    import zarr

    if out.exists():
        raise FileExistsError(out)
    level = presence_level(np.load(prob_path, mmap_mode="r"))
    out.parent.mkdir(parents=True, exist_ok=True)
    building = Path(tempfile.mkdtemp(prefix=f".{out.name}.building-", dir=out.parent))
    try:
        array = zarr.open(
            str(building / LEVEL),
            mode="w-",
            shape=level.shape,
            chunks=(64, 64, 64),
            dtype="u1",
            write_empty_chunks=True,  # every chunk on disk, so level_complete can tell
        )
        array[...] = level
        try:
            building.rename(out)
        except OSError:
            if out.exists():
                raise FileExistsError(
                    f"{out}: written by another writer meanwhile"
                ) from None
            raise
    except BaseException:
        shutil.rmtree(building, ignore_errors=True)
        raise
    return out / LEVEL


def level_complete(path: Path) -> bool:
    """True if every chunk of the presence level at PATH is on disk.

    A level this script writes has all of them (write_empty_chunks), and so does one written before 2026-10-17 by
    zarr 2.18's default. A missing chunk is a write that was killed: it reads as zero presence.
    """
    import zarr

    array = zarr.open(str(path), mode="r")
    return array.nchunks_initialized == array.nchunks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prob", type=Path)
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    print(write_presence(args.prob, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
