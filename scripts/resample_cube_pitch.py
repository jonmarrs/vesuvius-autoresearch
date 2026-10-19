"""docs/preregistration/2026-10-19_neural_tracer_training_pitch.md -- a ScrollGT fiber cube's CT and fiber
probability resampled to the voxel pitch villa's neural fiber tracer trained at.

The tracer feeds its network native CT voxels (crop_sampling/volume.py: "CT is read at its native resolution"), and
it needs a whole number of CT voxels per trace voxel, so no flag changes the pitch it sees. Finding 91 gave it the
cubes' own 7.91 um; its checkpoint trained on 8.64-9.6 um (its Scroll 1 source: 9.6 um). Here the cube is resampled
instead, to 9.6 um by default.

Sample j of the output is the source at j * r (r = to_um / from_um), trilinear, so a point traced at j in the
resampled cube is at j * r in the source cube (to_source). Edges are replicated, not zero-filled: the tracer reads CT
value 0 as outside the scan. Each output axis has an even length, for the 2x presence level.

Usage: .venv/bin/python scripts/resample_cube_pitch.py --ct SRC_ARRAY.zarr --prob SRC.npy \\
           --out-ct OUT.zarr --out-prob OUT.npy [--from-um 7.91] [--to-um 9.6]
       (writes OUT.zarr/0, the level the tracer reads with --ct-level 0)
"""

from __future__ import annotations

import argparse
import math
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import ndimage

FROM_UM = 7.91
TO_UM = 9.6
MULTIPLE = 2  # the presence level is 2x coarser than the CT


def resampled_length(n: int, r: float, multiple: int = MULTIPLE) -> int:
    """Samples at 0, r, 2r, ... that cover a source axis of n voxels, rounded up to a multiple of `multiple`."""
    k = math.floor((n - 1) / r) + 1
    return k + (-k) % multiple


def resample(volume: np.ndarray, r: float) -> np.ndarray:
    """Trilinear resampling: output[j] = volume[j * r] per axis, edges replicated. uint8 stays uint8 (rounded)."""
    shape = tuple(resampled_length(n, r) for n in volume.shape)
    out = ndimage.affine_transform(
        np.asarray(volume, dtype=np.float32),
        matrix=np.diag([r, r, r]),
        output_shape=shape,
        order=1,
        mode="nearest",
        output=np.float32,
    )
    if volume.dtype == np.uint8:
        return np.clip(np.rint(out), 0, 255).astype(np.uint8)
    return out


def to_source(points: np.ndarray, r: float) -> np.ndarray:
    """Resampled-cube coordinates (any axis order) -> source-cube coordinates."""
    return np.asarray(points, dtype=np.float64) * r


def _place(build: Path, out: Path) -> None:
    try:
        build.rename(out)
    except OSError:
        if out.exists():
            raise FileExistsError(
                f"{out}: written by another writer meanwhile"
            ) from None
        raise


def write_ct(src: Path, out: Path, r: float) -> tuple[int, ...]:
    """OUT/0: the resampled CT as a zarr v2 uint8 array (blosc lz4, 128^3 chunks), built beside OUT, then renamed."""
    import zarr
    from numcodecs import Blosc

    if out.exists():
        raise FileExistsError(out)
    ct = zarr.open(str(src), mode="r")
    if ct.dtype != np.uint8 or ct.ndim != 3:
        raise ValueError(
            f"{src}: expected a 3-D uint8 CT array, got {ct.dtype} {ct.shape}"
        )
    level = resample(ct[...], r)
    out.parent.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix=f".{out.name}.building-", dir=out.parent))
    try:
        arr = zarr.open(str(build / "0"), mode="w-", shape=level.shape, chunks=(128, 128, 128), dtype="u1",
                        compressor=Blosc(cname="lz4", clevel=5, shuffle=Blosc.SHUFFLE))  # fmt: skip
        arr[...] = level
        _place(build, out)
    except BaseException:
        shutil.rmtree(build, ignore_errors=True)
        raise
    return level.shape


def write_prob(src: Path, out: Path, r: float) -> tuple[int, ...]:
    """The resampled fiber probability, float32 in [0, 1], written beside OUT and renamed."""
    if out.exists():
        raise FileExistsError(out)
    prob = resample(np.load(src, mmap_mode="r"), r)
    np.clip(prob, 0.0, 1.0, out=prob)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{out.name}.", suffix=".npy", dir=out.parent)
    try:
        with open(fd, "wb") as fh:
            np.save(fh, prob)
        _place(Path(tmp), out)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return prob.shape


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ct", type=Path, required=True)
    ap.add_argument("--prob", type=Path, required=True)
    ap.add_argument("--out-ct", type=Path, required=True)
    ap.add_argument("--out-prob", type=Path, required=True)
    ap.add_argument("--from-um", type=float, default=FROM_UM)
    ap.add_argument("--to-um", type=float, default=TO_UM)
    args = ap.parse_args(argv)
    r = args.to_um / args.from_um
    # A resume keeps an output already written: each is built aside and renamed, so one that exists is whole.
    if args.out_ct.exists():
        import zarr

        ct_shape = tuple(zarr.open(str(args.out_ct / "0"), mode="r").shape)
    else:
        ct_shape = write_ct(args.ct, args.out_ct, r)
    prob_shape = (
        np.load(args.out_prob, mmap_mode="r").shape
        if args.out_prob.exists()
        else write_prob(args.prob, args.out_prob, r)
    )
    if ct_shape != prob_shape:
        raise SystemExit(
            f"CT {ct_shape} and probability {prob_shape} resampled to different shapes"
        )
    print(f"r={r:.6f} ct {ct_shape} prob {prob_shape}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
