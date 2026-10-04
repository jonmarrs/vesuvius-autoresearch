"""Run GPU fiber/ridge/vesselness detection on a .npy CT volume.

Usage:
    python -m vesuvius_autoresearch.fibers.cli --input vol.npy \
        --filter vesselness --output out.npy [--tiled --block-size 128 --halo 16] \
        [--preview out.png]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from vesuvius_autoresearch.fibers import (
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
)


def _backend(volume, device):
    if device == "cpu":
        return volume, "cpu"
    try:
        import cupy as cp
    except ImportError as exc:
        if device == "gpu":
            raise RuntimeError("GPU requested but CuPy is unavailable") from exc
        return volume, "cpu"
    try:
        available = cp.cuda.runtime.getDeviceCount() > 0
    except cp.cuda.runtime.CUDARuntimeError as exc:
        if device == "gpu":
            raise RuntimeError("GPU requested but CUDA is unavailable") from exc
        print(f"CUDA unavailable; using CPU: {exc}", file=sys.stderr)
        return volume, "cpu"
    if not available:
        if device == "gpu":
            raise RuntimeError("GPU requested but no CUDA device is visible")
        return volume, "cpu"
    # Allocation/filter failures on a usable GPU must remain failures.
    return cp.asarray(volume), "gpu"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GPU fiber/ridge/vesselness detection.")
    ap.add_argument("--input", required=True, help="input .npy CT volume [Z,H,W]")
    ap.add_argument("--filter", choices=["vesselness", "ridges"], default="vesselness")
    ap.add_argument("--output", required=True, help="output .npy path")
    ap.add_argument(
        "--tiled", action="store_true", help="tiled/halo execution for large volumes"
    )
    ap.add_argument("--block-size", type=int, default=128)
    ap.add_argument("--halo", type=int, default=16)
    ap.add_argument("--preview", help="optional z-mean preview PNG")
    ap.add_argument("--device", choices=["auto", "cpu", "gpu"], default="auto")
    args = ap.parse_args(argv)

    from vesuvius_autoresearch.fibers.detection import _volume

    vol = _volume(np.load(args.input, allow_pickle=False))
    arr, backend = _backend(vol, args.device)

    if args.filter == "vesselness":
        fn = detect_vesselness_tiled if args.tiled else detect_vesselness
    else:
        fn = detect_ridges_tiled if args.tiled else detect_ridges
    kwargs = {"block_size": args.block_size, "halo": args.halo} if args.tiled else {}

    t0 = time.time()
    out = fn(arr, **kwargs)
    try:
        import cupy as cp

        if isinstance(out, cp.ndarray):
            out = cp.asnumpy(out)
    except ImportError:
        pass
    out = np.asarray(out, dtype=np.float32)
    if out.shape != vol.shape or not np.isfinite(out).all():
        raise ValueError("filter output must be finite and match the CT volume")
    dt = time.time() - t0

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, out)
    print(
        f"{args.filter} backend={backend} tiled={args.tiled} shape={out.shape} "
        f"time={dt:.2f}s -> {args.output}"
    )

    if args.preview:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        Path(args.preview).parent.mkdir(parents=True, exist_ok=True)
        plt.imsave(args.preview, out.mean(axis=0), cmap="magma")
        print(f"preview -> {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
