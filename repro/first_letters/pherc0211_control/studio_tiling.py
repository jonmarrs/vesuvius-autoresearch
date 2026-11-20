"""Finding 128: Studio's published tiling (96-pixel windows, no overlap) against the winner's (64, Hann-blended).

Registration: docs/preregistration/2026-11-20_studio_published_tiling.md.

    studio_tiling.py OUT.json FAST.npy SLOW.npy MASK.png --gate GATE.json

FAST.npy is inference.py's map with the published tiling, SLOW.npy finding 123's with the winner's command, both
of the winner's 16-plane input. Compared over the winner's mask with finding 123's `compare`. Measured once.
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


def main(argv: list[str] | None = None) -> int:
    import cv2

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
