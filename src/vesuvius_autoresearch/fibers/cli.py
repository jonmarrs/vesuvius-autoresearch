"""Run GPU fiber/ridge/vesselness detection on a .npy CT volume.

Usage:
    python -m vesuvius_autoresearch.fibers.cli --input vol.npy \
        --filter vesselness --output out.npy [--tiled --block-size 128 --halo 16] \
        [--preview out.png]
"""

import argparse
import time

import numpy as np

from vesuvius_autoresearch.fibers import (
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
)


def main() -> int:
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
    args = ap.parse_args()

    vol = np.load(args.input).astype(np.float32)
    backend = "cpu"
    arr = vol
    try:
        import cupy as cp

        arr = cp.asarray(vol)
        backend = "gpu"
    except ImportError:
        pass

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
    dt = time.time() - t0

    np.save(args.output, out)
    print(
        f"{args.filter} backend={backend} tiled={args.tiled} shape={out.shape} "
        f"time={dt:.2f}s -> {args.output}"
    )

    if args.preview:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.imsave(args.preview, out.mean(axis=0), cmap="magma")
        print(f"preview -> {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
