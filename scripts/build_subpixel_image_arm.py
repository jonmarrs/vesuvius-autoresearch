"""Build a scorer-only arm: a strip re-sampled HALF A PIXEL along x, as an image.

`docs/preregistration/2026-09-24_scorer_subpixel.md`. The rendered half-pixel
re-sample (`rs_t005`) re-drew 0.088 per 2 kpx block; whole-pixel moves of identical
pixels re-draw 0.0001. This asks whether the scorer alone does it: the reference
strip's OWN pixels, linearly interpolated to x + 0.5 (the mean of each pixel and
its right neighbour, rounded), same canvas, lossless PNG. No render involved.

Usage:
    build_subpixel_image_arm.py <src scored arm> <out arm>
"""

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_shifted_strip_arm import NAME, load_strip  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def half_pixel_shift_x(s: np.ndarray) -> np.ndarray:
    """Value at x + 0.5 by linear interpolation; the last column is kept."""
    out = s.copy()
    a = s[:, :-1].astype(np.uint16)
    b = s[:, 1:].astype(np.uint16)
    out[:, :-1] = ((a + b + 1) // 2).astype(np.uint8)  # round half up
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src_arm")
    ap.add_argument("out_arm")
    a = ap.parse_args()
    src, out = Path(a.src_arm), Path(a.out_arm)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite")
    s = load_strip(src / "meshes" / "ink")
    h = half_pixel_shift_x(s)
    ink = out / "meshes" / "ink"
    ink.mkdir(parents=True)
    p = ink / f"{NAME}.png"
    Image.fromarray(h).save(p, optimize=False, compress_level=1)
    if not np.array_equal(np.asarray(Image.open(p)), h):
        raise SystemExit(f"round-trip mismatch in {p}")
    shutil.copytree(src / "spiral-fitting", out / "spiral-fitting", symlinks=True)
    for f in ("VILLA_SHA", "RENDER_IMAGE"):
        if (src / f).exists():
            shutil.copy2(src / f, out / f)
    diff = np.abs(h.astype(np.int16) - s.astype(np.int16))
    print(f"built {out}: mean |dpixel| {diff.mean():.3f}, max {diff.max()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
