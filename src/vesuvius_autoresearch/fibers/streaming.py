"""Two-pass CLI filtering with host-backed input/output and bounded transfers.

The existing in-memory APIs and filter math remain in detection.py. This path
uses their Gaussian normalization and filters on one halo block at a time.
"""

import math

import numpy as np

from .detection import _volume, detect_ridges, detect_vesselness, get_backend

GAUSS_SIGMA = 2


def validate_tiling(block_size, halo):
    if (
        isinstance(block_size, (bool, np.bool_))
        or not isinstance(block_size, (int, np.integer))
        or block_size <= 0
    ):
        raise ValueError("block_size must be a positive integer")
    required = int(4 * GAUSS_SIGMA + 0.5) + 2
    if (
        isinstance(halo, (bool, np.bool_))
        or not isinstance(halo, (int, np.integer))
        or halo < required
    ):
        raise ValueError(f"halo must be an integer >= {required}")


def blocks(shape, block_size, halo):
    """Yield source, source-interior, and destination slices without a tile list."""
    for z in range(0, shape[0], block_size):
        for y in range(0, shape[1], block_size):
            for x in range(0, shape[2], block_size):
                starts = (z, y, x)
                lower = [max(0, a - halo) for a in starts]
                upper = [
                    min(n, a + block_size + halo)
                    for a, n in zip(starts, shape, strict=True)
                ]
                widths = [
                    min(block_size, n - a) for a, n in zip(starts, shape, strict=True)
                ]
                source = tuple(slice(a, b) for a, b in zip(lower, upper, strict=True))
                interior = tuple(
                    slice(a - lo, a - lo + width)
                    for a, lo, width in zip(starts, lower, widths, strict=True)
                )
                destination = tuple(
                    slice(a, a + width) for a, width in zip(starts, widths, strict=True)
                )
                yield source, interior, destination


def filter_into(
    volume,
    output,
    *,
    filter_name,
    block_size=128,
    halo=16,
    to_device=np.asarray,
    to_host=np.asarray,
    release=None,
):
    """Write float32 responses into a separate host array or disk memory map.

    Inputs must stay stable across both passes. ``to_device`` sees only halo
    blocks; ``to_host`` receives only the core response. CUDA allocation and
    filter failures propagate without a change of backend.
    """
    validate_tiling(block_size, halo)
    if (
        not isinstance(volume, np.ndarray)
        or volume.ndim != 3
        or min(volume.shape) < 3
        or volume.dtype.kind not in "uif"
    ):
        raise ValueError("volume must be a real CT array with each axis at least 3")
    if (
        not isinstance(output, np.ndarray)
        or output.shape != volume.shape
        or output.dtype != np.float32
        or not output.flags.writeable
        or np.shares_memory(volume, output)
    ):
        raise ValueError(
            "output must be a separate writable float32 array matching CT shape"
        )
    if filter_name not in {"ridges", "vesselness"}:
        raise ValueError("unknown fiber filter")
    filter_fn = detect_ridges if filter_name == "ridges" else detect_vesselness

    low, high = math.inf, -math.inf
    for source, interior, _ in blocks(volume.shape, block_size, halo):
        block = to_device(_volume(volume[source]))
        _, ndimage = get_backend(block)
        smoothed = ndimage.gaussian_filter(block, sigma=GAUSS_SIGMA)
        core = smoothed[interior]
        block_low, block_high = float(core.min()), float(core.max())
        if not math.isfinite(block_low) or not math.isfinite(block_high):
            raise ValueError("smoothing produced nonfinite extrema")
        low, high = min(low, block_low), max(high, block_high)
        del core, smoothed, block
        if release is not None:
            release()

    for source, interior, destination in blocks(volume.shape, block_size, halo):
        block = to_device(_volume(volume[source]))
        result = filter_fn(block, gauss_sigma=GAUSS_SIGMA, norm_range=(low, high))
        if result.shape != block.shape or result.dtype.kind != "f":
            raise ValueError(
                "filter output must be floating-point and match the halo block"
            )
        core = np.asarray(to_host(result[interior]), dtype=np.float32)
        if core.shape != output[destination].shape or not np.isfinite(core).all():
            raise ValueError("filter output must be finite and match the core block")
        output[destination] = core
        del core, result, block
        if release is not None:
            release()
