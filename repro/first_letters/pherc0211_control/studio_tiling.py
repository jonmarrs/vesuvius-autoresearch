"""Finding 128: Studio's published tiling (96-pixel windows, no overlap) against the winner's (64, Hann-blended).

Registration: docs/preregistration/2026-11-20_studio_published_tiling.md.

    studio_tiling.py OUT.json FAST.npy SLOW.npy MASK.png --gate GATE.json

FAST.npy is inference.py's map with the published tiling, SLOW.npy finding 123's with the winner's command, both
of the winner's 16-plane input. Compared over the winner's mask with finding 123's `compare`. Measured once.

    studio_tiling.py seams OUT.json FAST.npy SLOW.npy MASK.png

Described after the verdict, deciding nothing: the mean absolute difference over the mask by position within the
published tiling's 96-pixel windows, on their edges (the first and last pixel) and in their middle (pixels 32 to 63),
along columns and along rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import studio_reproduce as f123  # noqa: E402

R_LINE, SAME_SIDE_LINE = 0.98, 0.98
SLOW_SECONDS = 75  # finding 123's run with the winner's command


def verdict(gate_exit: int | None, numbers: dict | None) -> str:
    if gate_exit != 0 or numbers is None:
        return "DOES_NOT_RUN"
    if numbers["r"] >= R_LINE and numbers["share_same_side_of_half"] >= SAME_SIDE_LINE:
        return "PUBLISHED_TILING_ADOPTED"
    return "WINNERS_TILING_KEPT"


PERIOD = 96  # the published tiling's written window


def seam_profile(fast: np.ndarray, slow: np.ndarray, mask: np.ndarray) -> dict:
    d = np.abs(fast.astype(np.float64) - slow.astype(np.float64))

    def along(axis: int) -> dict:
        pos = np.arange(d.shape[axis]) % PERIOD
        pos = pos[None, :] if axis == 1 else pos[:, None]
        pos = np.broadcast_to(pos, d.shape)[mask]
        vals = d[mask]
        edge = (pos == 0) | (pos == PERIOD - 1)
        middle = (pos >= 32) & (pos < 64)
        return {
            "edge": round(float(vals[edge].mean()), 6) if edge.any() else None,
            "middle": round(float(vals[middle].mean()), 6) if middle.any() else None,
        }

    return {
        "period": PERIOD,
        "pixels": int(mask.sum()),
        "columns": along(1),
        "rows": along(0),
    }


def seams(argv: list[str]) -> int:
    import cv2

    ap = argparse.ArgumentParser(prog="studio_tiling.py seams")
    for name in ("out", "fast", "slow", "mask"):
        ap.add_argument(name, type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    mask_px = cv2.imread(str(args.mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.mask}")
    profile = seam_profile(
        np.load(args.fast, allow_pickle=False),
        np.load(args.slow, allow_pickle=False),
        mask_px > 0,
    )
    result = {
        "finding": 128,
        "described_after_the_verdict": True,
        "seam_profile": profile,
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    import cv2

    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["seams"]:
        return seams(argv[1:])

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("fast", type=Path)
    ap.add_argument("slow", type=Path)
    ap.add_argument("mask", type=Path)
    ap.add_argument("--gate", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    gate = json.loads(args.gate.read_text()) if args.gate.exists() else {"exit": None}
    numbers = None
    if gate.get("exit") == 0 and args.fast.exists():
        mask_px = cv2.imread(str(args.mask), cv2.IMREAD_GRAYSCALE)
        if mask_px is None:
            raise SystemExit(f"cannot read {args.mask}")
        numbers = f123.compare(
            np.load(args.fast, allow_pickle=False),
            np.load(args.slow, allow_pickle=False),
            mask_px > 0,
        )
    result = {
        "finding": 128,
        "infer": gate,
        "seconds_winners_tiling": SLOW_SECONDS,
        "numbers": numbers,
        "verdict": verdict(gate.get("exit"), numbers),
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
