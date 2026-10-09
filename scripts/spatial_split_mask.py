"""Prepare two mask-pixel partitions and an exact discarded buffer strip.

Publish a new directory containing u.png, v.png, and split.json with --out.
Mask disjointness alone does not prove that sampled CT patches are independent.
Legacy --out-u/--out-v file pairs are retired to allow complete pair publication.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import integer, write_json
from scripts.labeling.label_artifacts import bounded_number, new_output, publish_new
from scripts.pseudo_label_artifacts import MAX_LABEL_PIXELS, binary_array, read_png


def split_bounds(shape, axis, fraction, buffer):
    if any(isinstance(v, (bool, np.bool_)) for v in (axis, fraction, buffer)):
        raise ValueError("axis, fraction, and buffer must be numeric, not boolean")
    axis = integer(axis, "axis")
    if axis not in (0, 1):
        raise ValueError("axis must be 0 (y) or 1 (x)")
    fraction = bounded_number(fraction, "fraction", 0, 1)
    if not 0 < fraction < 1:
        raise ValueError("fraction must lie strictly between 0 and 1")
    buffer = integer(buffer, "buffer")
    split = int(shape[axis] * fraction)
    lo = split - buffer // 2
    hi = split + buffer - buffer // 2
    if not 0 < lo <= hi < shape[axis]:
        raise ValueError("split and exact buffer must leave space on both sides")
    return axis, fraction, buffer, split, lo, hi


def split_mask(
    mask: np.ndarray, axis: int = 1, fraction: float = 0.5, buffer: int = 128
):
    """Keep low/high indices; odd gaps discard their extra pixel on the high side."""
    mask = binary_array(mask, "surface mask")
    axis, _, _, _, lo, hi = split_bounds(mask.shape, axis, fraction, buffer)
    u, v = mask.copy(), mask.copy()
    lower, upper = [slice(None)] * 2, [slice(None)] * 2
    lower[axis] = slice(lo, None)
    upper[axis] = slice(None, hi)
    u[tuple(lower)] = False
    v[tuple(upper)] = False
    if not u.any() or not v.any():
        raise ValueError("both partitions must contain positive source pixels")
    return u, v


def prepare_split(
    mask_path, output, *, axis=1, fraction=0.5, buffer=128, max_pixels=MAX_LABEL_PIXELS
):
    from scripts.export_for_production import sha256_file

    source = Path(mask_path).resolve()
    output = new_output(output, source)
    digest = sha256_file(source)
    mask = read_png(source, kind="binary", max_pixels=max_pixels)
    u, v = split_mask(mask, axis, fraction, buffer)
    axis, fraction, buffer, boundary, lo, hi = split_bounds(
        mask.shape, axis, fraction, buffer
    )
    result = {
        "schema": "spatial-mask-split-v1",
        "status": "PREPARED",
        "scope": "mask_pixel_partition",
        "source": str(source),
        "source_sha256": digest,
        "shape_yx": list(mask.shape),
        "axis": axis,
        "fraction": fraction,
        "split_index": boundary,
        "buffer_width": buffer,
        "gap_indices": [lo, hi],
        "source_positive_pixels": int(mask.sum()),
        "u_positive_pixels": int(u.sum()),
        "v_positive_pixels": int(v.sum()),
        "discarded_positive_pixels": int(mask.sum() - u.sum() - v.sum()),
        "mask_pixels_disjoint": True,
        "patch_independence_verified": False,
        "training_executed": False,
        "max_pixels": integer(max_pixels, "max_pixels", 1),
        "outputs": {},
    }
    with publish_new(output) as staging:
        for name, values in (("u.png", u), ("v.png", v)):
            path = staging / name
            Image.fromarray(values.astype(np.uint8) * 255).save(path)
            actual = read_png(
                path, kind="binary", shape=mask.shape, max_pixels=max_pixels
            )
            if not np.array_equal(values, actual):
                raise ValueError("written partition differs from validated mask")
            result["outputs"][name] = {"path": name, "sha256": sha256_file(path)}
        if sha256_file(source) != digest:
            raise ValueError("source mask changed during preparation")
        write_json(staging / "split.json", result)
    return result


def main(argv=None):
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mask", required=True, help="binary source mask PNG")
    ap.add_argument(
        "--out", required=True, help="new, source-disjoint artifact directory"
    )
    ap.add_argument("--axis", type=int, default=1)
    ap.add_argument("--fraction", type=float, default=0.5)
    ap.add_argument("--buffer", type=int, default=128)
    ap.add_argument("--max-pixels", type=int, default=MAX_LABEL_PIXELS)
    args = ap.parse_args(argv)
    try:
        result = prepare_split(
            args.mask,
            args.out,
            axis=args.axis,
            fraction=args.fraction,
            buffer=args.buffer,
            max_pixels=args.max_pixels,
        )
    except (ValueError, OSError) as exc:
        ap.exit(1, f"spatial mask split: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
