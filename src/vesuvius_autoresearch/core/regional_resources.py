"""Allocation-free limits for the regional predictors' persistent blend arrays.

This is not a peak RAM/VRAM estimate: weights, activations, normalization and
export temporaries, storage decoding and host copies need additional memory.
"""

MAX_ACCUMULATOR_BYTES = 512 * 1024**2


def plan_regional_accumulators(
    width, height, max_accumulator_bytes=MAX_ACCUMULATOR_BYTES
):
    for name, value in (
        ("width", width),
        ("height", height),
        ("max_accumulator_bytes", max_accumulator_bytes),
    ):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    # Both predictors retain ink, fiber and weight planes even without a fiber
    # head or when processing a shard. Their allocations explicitly use float32.
    size = width * height * 3 * 4
    if size > max_accumulator_bytes:
        raise ValueError(
            f"regional accumulator bytes {size} exceed "
            f"max_accumulator_bytes={max_accumulator_bytes}; use a smaller region "
            "or explicitly raise --max_accumulator_bytes after checking capacity. "
            "Sharding tiles does not shrink these arrays."
        )
    return {
        "schema_version": 1,
        "width": width,
        "height": height,
        "accumulator_arrays": 3,
        "accumulator_dtype": "float32",
        "accumulator_bytes": size,
        "max_accumulator_bytes": max_accumulator_bytes,
        "whole_process_peak_estimated": False,
    }
