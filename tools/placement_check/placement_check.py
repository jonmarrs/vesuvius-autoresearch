"""Does your registered ground truth actually sit where it claims to?

A registration is only correct if agreement between the label and a reference peaks at
ZERO shift. That sounds obvious. It is also, in our experience, the check nobody runs.

We shipped a ground-truth benchmark whose registration reported a median correspondence
residual of 8 voxels. The label was displaced by 1766. Both statements were true at once:
a residual measures how much correspondences SCATTER, and says nothing about where the
result sits. Every model scored against that label looked like it was reading at chance,
including models that were reading fine. The error survived a residual gate, an
orientation check, a text-line periodicity check, and a published leaderboard, for a month.

This module is the ten lines that would have caught it on day one.

    from placement_check import placement_offset
    r = placement_offset(my_label, reference)
    if not r.passed(max_offset=8):
        raise SystemExit(f"label is {r.offset:.1f} px out of place at {r.dy, r.dx}")

Numpy only. `label` and `reference` are 2-D arrays of the same shape; bool is used as-is,
anything else is thresholded at >127.

Interpreting the result
-----------------------
`offset` is in input pixels. What counts as acceptable is domain-specific, and it is worth
converting to units that mean something: if you analyse in NxN windows, an offset
approaching N means a prediction and the label it is scored against need not overlap at
all, and the score is measuring something else. Below a fraction of a window it is
tolerable smearing. We set our own gate by measuring the floor imposed by our data, then
sitting just above it, and we wrote down why.

A peak far from zero does not tell you WHICH artifact moved. It tells you two things
disagree. Finding out which one is wrong is a separate job, and worth doing before you
"correct" anything by the measured offset: fitting a shift to make a number improve is how
you turn a registration bug into a permanent fudge factor.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import asdict, dataclass

import numpy as np

__all__ = ["placement_offset", "PlacementResult"]
__version__ = "0.1.0"


@dataclass(frozen=True)
class PlacementResult:
    """Where label-vs-reference agreement actually peaks."""

    dy: int
    dx: int
    offset: float
    dice_at_zero: float
    dice_at_peak: float

    def passed(self, max_offset: float) -> bool:
        return self.offset <= max_offset

    def as_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return (
            f"peak at (dy={self.dy}, dx={self.dx}), offset {self.offset:.1f} px; "
            f"dice {self.dice_at_zero:.4f} at zero, {self.dice_at_peak:.4f} at peak"
        )


def _binarise(x, what: str) -> np.ndarray:
    x = np.asarray(x)
    if x.ndim != 2:
        raise ValueError(f"placement_offset: {what} must be 2-D, got shape {x.shape}")
    # Bool is taken as-is. Thresholding a bool array at >127 yields all-False, which makes
    # every comparison degenerate and returns a PERFECT (0, 0): a check that silently
    # passes on garbage. That bug is exactly the failure mode this module exists to stop,
    # so it is guarded rather than documented.
    m = x if x.dtype == bool else x > 127
    if not m.any():
        raise ValueError(
            f"placement_offset: {what} is empty after binarisation (dtype={x.dtype}, "
            f"min={x.min()}, max={x.max()}). An empty mask cannot be placed; pass a "
            "labelled image."
        )
    return m


def _dice(a: np.ndarray, b: np.ndarray) -> float:
    total = int(a.sum()) + int(b.sum())
    return 2.0 * float(np.logical_and(a, b).sum()) / total if total else float("nan")


def _scan(fixed, moving, margin, lo, hi):
    """Best Dice over integer shifts, comparing on a common interior crop.

    Never np.roll: wraparound would fold content from one edge onto the other and score it
    as agreement.
    """
    h, w = fixed.shape
    core = fixed[margin : h - margin, margin : w - margin]
    best = (-1.0, 0, 0)
    for dy in range(lo[0], hi[0] + 1):
        for dx in range(lo[1], hi[1] + 1):
            d = _dice(
                core,
                moving[margin + dy : h - margin + dy, margin + dx : w - margin + dx],
            )
            if d > best[0]:
                best = (d, dy, dx)
    return best


def _downsample(mask: np.ndarray, factor: int) -> np.ndarray:
    """Nearest-neighbour decimation. Numpy only, so this has no OpenCV dependency."""
    return mask[::factor, ::factor] if factor > 1 else mask


def placement_offset(
    label, reference, max_shift: int = 256, coarse: int = 4, refine: int = 8
) -> PlacementResult:
    """Locate the shift at which `label` best agrees with `reference`.

    Returns (0, 0) for a correctly placed label. `max_shift` bounds the search in input
    pixels and must exceed the error you are willing to detect: a peak pinned to the
    search boundary is under-reported, and this raises rather than returning it.
    """
    a = _binarise(label, "label")
    b = _binarise(reference, "reference")
    if a.shape != b.shape:
        raise ValueError(f"placement_offset: shape mismatch {a.shape} vs {b.shape}")

    ds = max(int(coarse), 1)
    a_s, b_s = _downsample(a, ds), _downsample(b, ds)
    m_s = max_shift // ds + 2
    if min(a_s.shape) <= 2 * m_s + 2:
        m_s = max(min(a_s.shape) // 4, 1)
    _, cy, cx = _scan(a_s, b_s, m_s, (-m_s, -m_s), (m_s, m_s))
    cy, cx = cy * ds, cx * ds

    margin = max_shift + refine + 2
    if min(a.shape) <= 2 * margin + 2:
        margin = max(min(a.shape) // 4, 1)
    cy = int(np.clip(cy, -margin + refine, margin - refine))
    cx = int(np.clip(cx, -margin + refine, margin - refine))
    peak, by, bx = _scan(
        a, b, margin, (cy - refine, cx - refine), (cy + refine, cx + refine)
    )

    if max(abs(by), abs(bx)) >= max_shift:
        raise ValueError(
            f"placement_offset: peak reached the search boundary at ({by}, {bx}); the true "
            f"offset is at least this and probably larger. Re-run with max_shift > "
            f"{max_shift}."
        )

    h, w = a.shape
    zero = _dice(
        a[margin : h - margin, margin : w - margin],
        b[margin : h - margin, margin : w - margin],
    )
    return PlacementResult(
        int(by), int(bx), float(np.hypot(by, bx)), float(zero), float(peak)
    )


def _load(path: str) -> np.ndarray:
    if path.endswith(".npy"):
        return np.load(path)
    try:
        from PIL import Image
    except ImportError as err:  # pragma: no cover
        raise SystemExit(
            "reading image files needs Pillow; use .npy or `pip install pillow`"
        ) from err
    Image.MAX_IMAGE_PIXELS = None
    arr = np.array(Image.open(path))
    return arr[..., 0] if arr.ndim == 3 else arr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="Exits 1 if the offset exceeds --max-offset, so it can gate a pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("label", help="registered label (.png/.tif/.npy)")
    ap.add_argument("reference", help="what it should agree with, same shape")
    ap.add_argument("--max-shift", type=int, default=256, help="search bound, px")
    ap.add_argument(
        "--max-offset",
        type=float,
        default=None,
        help="fail if the offset exceeds this (px). Omit to just report.",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    for p in (args.label, args.reference):
        if not os.path.exists(p):
            raise SystemExit(f"no such file: {p}")
    r = placement_offset(
        _load(args.label), _load(args.reference), max_shift=args.max_shift
    )

    if args.json:
        import json

        print(json.dumps(r.as_dict(), indent=2))
    else:
        print(r)
        if r.offset > 0:
            print(
                f"  agreement improves {r.dice_at_peak - r.dice_at_zero:+.4f} when shifted, "
                "which it should not for a correctly placed label"
            )
    if args.max_offset is not None and not r.passed(args.max_offset):
        print(
            f"FAIL: offset {r.offset:.1f} px exceeds {args.max_offset:g} px",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
