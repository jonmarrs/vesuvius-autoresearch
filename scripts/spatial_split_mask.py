"""Split a 2D boolean surface mask into two spatially-disjoint region masks
separated by a discarded buffer strip, so patches sampled from each region
share no pixels (train/predict non-overlap).
"""

import argparse

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def split_mask(
    mask: np.ndarray, axis: int = 1, fraction: float = 0.5, buffer: int = 128
):
    """Return (u_mask, v_mask): the original mask restricted to the low-index
    region and high-index region along `axis`, with a `buffer`-wide gap between
    them removed from both. fraction sets the split point along `axis`.
    """
    n = mask.shape[axis]
    split = int(n * fraction)
    lo_end = split - buffer // 2
    hi_start = split + buffer // 2
    u = mask.copy()
    v = mask.copy()
    idx_u = [slice(None)] * mask.ndim
    idx_v = [slice(None)] * mask.ndim
    idx_u[axis] = slice(lo_end, None)
    idx_v[axis] = slice(None, hi_start)
    u[tuple(idx_u)] = False
    v[tuple(idx_v)] = False
    return u, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mask", required=True, help="path to mask.png")
    ap.add_argument("--out-u", required=True)
    ap.add_argument("--out-v", required=True)
    ap.add_argument("--axis", type=int, default=1)
    ap.add_argument("--fraction", type=float, default=0.5)
    ap.add_argument("--buffer", type=int, default=128)
    args = ap.parse_args()

    mask = np.array(Image.open(args.mask).convert("L")) > 127
    u, v = split_mask(mask, args.axis, args.fraction, args.buffer)
    Image.fromarray((u * 255).astype(np.uint8)).save(args.out_u)
    Image.fromarray((v * 255).astype(np.uint8)).save(args.out_v)
    print(
        f"U maskpx={int(u.sum()):,} V maskpx={int(v.sum()):,} "
        f"disjoint={not bool((u & v).any())}"
    )


if __name__ == "__main__":
    main()
