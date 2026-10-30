"""Run GPU fiber/ridge/vesselness detection on a .npy CT volume.

Usage:
    python -m vesuvius_autoresearch.fibers.cli --input vol.npy \
        --filter vesselness --output out.npy [--tiled --block-size 128 --halo 16] \
        [--preview out.png]
"""

import argparse
import sys
import time

import numpy as np

from vesuvius_autoresearch.fibers import (
    detect_ridges,
    detect_vesselness,
)


def _array_backend(device):
    if device == "cpu":
        return np, "cpu"
    try:
        import cupy as cp
    except ImportError as exc:
        if device == "gpu":
            raise RuntimeError("GPU requested but CuPy is unavailable") from exc
        return np, "cpu"
    try:
        available = cp.cuda.runtime.getDeviceCount() > 0
    except cp.cuda.runtime.CUDARuntimeError as exc:
        if device == "gpu":
            raise RuntimeError("GPU requested but CUDA is unavailable") from exc
        print(f"CUDA unavailable; using CPU: {exc}", file=sys.stderr)
        return np, "cpu"
    if not available:
        if device == "gpu":
            raise RuntimeError("GPU requested but no CUDA device is visible")
        return np, "cpu"
    # Allocation/filter failures on a usable GPU must remain failures.
    return cp, "gpu"


def _backend(volume, device):
    xp, name = _array_backend(device)
    return xp.asarray(volume), name


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GPU fiber/ridge/vesselness detection.")
    ap.add_argument("--input", required=True, help="input .npy CT volume [Z,H,W]")
    ap.add_argument("--filter", choices=["vesselness", "ridges"], default="vesselness")
    ap.add_argument("--output", required=True, help="output .npy path")
    ap.add_argument(
        "--tiled",
        action="store_true",
        help="stream halo blocks from disk; memory-map the float32 output",
    )
    ap.add_argument("--block-size", type=int, default=128)
    ap.add_argument("--halo", type=int, default=16)
    ap.add_argument("--preview", help="optional z-mean preview PNG")
    ap.add_argument("--device", choices=["auto", "cpu", "gpu"], default="auto")
    args = ap.parse_args(argv)

    from vesuvius_autoresearch.fibers import filter_artifacts, streaming
    from vesuvius_autoresearch.fibers.detection import _volume

    filter_artifacts.validate_paths(args.input, args.output, args.preview)
    signature = filter_artifacts.input_signature(args.input)
    if args.tiled:
        streaming.validate_tiling(args.block_size, args.halo)
    t0 = time.time()
    with (
        filter_artifacts.mapped_input(args.input) as volume,
        filter_artifacts.staged_file(args.output) as temporary,
        filter_artifacts.staged_file(args.preview) as preview_temporary,
    ):
        shape = volume.shape
        if args.tiled:
            xp, backend = _array_backend(args.device)
            pool = (
                xp.get_default_memory_pool()
                if backend == "gpu" and hasattr(xp, "get_default_memory_pool")
                else None
            )
            with filter_artifacts.mapped_output(temporary, shape) as response:
                streaming.filter_into(
                    volume,
                    response,
                    filter_name=args.filter,
                    block_size=args.block_size,
                    halo=args.halo,
                    to_device=xp.asarray,
                    to_host=xp.asnumpy if backend == "gpu" else np.asarray,
                    release=pool.free_all_blocks if pool is not None else None,
                )
                projection = response.mean(axis=0) if args.preview else None
        else:
            arr, backend = _backend(_volume(volume), args.device)
            fn = detect_vesselness if args.filter == "vesselness" else detect_ridges
            out = fn(arr)
            if backend == "gpu":
                import cupy as cp

                out = cp.asnumpy(out)
            out = np.asarray(out, dtype=np.float32)
            if out.shape != shape or not np.isfinite(out).all():
                raise ValueError("filter output must be finite and match the CT volume")
            with temporary.open("wb") as stream:
                np.save(stream, out, allow_pickle=False)
            projection = out.mean(axis=0) if args.preview else None
        if args.preview:
            filter_artifacts.write_preview(preview_temporary, projection)
        filter_artifacts.publish(
            args.input,
            signature,
            args.output,
            temporary,
            args.preview,
            preview_temporary,
        )
    dt = time.time() - t0

    print(
        f"{args.filter} backend={backend} tiled={args.tiled} shape={shape} "
        f"time={dt:.2f}s -> {args.output}"
    )

    if args.preview:
        print(f"preview -> {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
