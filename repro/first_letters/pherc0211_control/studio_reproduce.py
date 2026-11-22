"""Finding 123: does Studio, run here from the winner's supplied weights and input, reproduce the winner's map?

Registration: docs/preregistration/2026-11-16_first_letters_0211_studio_reproduction.md.

    studio_reproduce.py OUT.json OURS.npy WINNER.tif MASK.png [--gate GATE.json]

OURS.npy is inference.py's output (float32 [H, W]); WINNER.tif the published probability map (float32); the mask
the winner's studiosoft-mask. Compared over the mask's pixels: the output's SHA-256 against the record's, r, and the
distribution of absolute differences. Measured once: OUT must not exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

RECORDED_NPY_SHA256 = "e2f8b9afad4dcde91a6775713b5da1e08352ac38adf39e7e75cb9f4b181bd139"
R_REPRODUCED = 0.99
P99_REPRODUCED = 0.05  # probability units


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare(ours: np.ndarray, theirs: np.ndarray, mask: np.ndarray) -> dict:
    if ours.shape != theirs.shape or mask.shape != ours.shape:
        raise ValueError(
            f"shapes differ: ours {ours.shape}, winner's {theirs.shape}, mask {mask.shape}"
        )
    a, b = ours[mask].astype(np.float64), theirs[mask].astype(np.float64)
    finite = np.isfinite(a) & np.isfinite(b)
    a, b = a[finite], b[finite]
    diff = np.abs(a - b)
    q = np.percentile(diff, [50, 99, 100])
    return {
        "pixels": int(a.size),
        "r": round(float(np.corrcoef(a, b)[0, 1]), 6),
        "abs_difference": {
            "p50": round(float(q[0]), 6),
            "p99": round(float(q[1]), 6),
            "max": round(float(q[2]), 6),
        },
        "mean_ours": round(float(a.mean()), 6),
        "mean_winner": round(float(b.mean()), 6),
        "share_same_side_of_half": round(float(((a >= 0.5) == (b >= 0.5)).mean()), 6),
    }


def verdict(gate_exit: int | None, exact: bool | None, numbers: dict | None) -> str:
    if gate_exit != 0 or numbers is None:
        return "DOES_NOT_RUN"
    if exact:
        return "EXACT"
    if (
        numbers["r"] >= R_REPRODUCED
        and numbers["abs_difference"]["p99"] <= P99_REPRODUCED
    ):
        return "REPRODUCED"
    return "DIFFERS"


def main(argv: list[str] | None = None) -> int:
    import cv2
    import tifffile

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("ours", type=Path)
    ap.add_argument("winner", type=Path)
    ap.add_argument("mask", type=Path)
    ap.add_argument("--gate", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    gate = (
        json.loads(args.gate.read_text())
        if args.gate and args.gate.exists()
        else {"exit": 0}
    )
    result: dict = {"finding": 123, "inference": gate}
    numbers = exact = None
    if gate.get("exit") == 0 and args.ours.exists():
        exact = sha256(args.ours) == RECORDED_NPY_SHA256
        ours = np.load(args.ours, allow_pickle=False)
        theirs = tifffile.imread(args.winner)
        mask_px = cv2.imread(str(args.mask), cv2.IMREAD_GRAYSCALE)
        if mask_px is None:
            raise SystemExit(f"cannot read {args.mask}")
        numbers = compare(ours, theirs, mask_px > 0)
        result.update({"output_sha256": sha256(args.ours), "exact": exact})
    result["numbers"] = numbers
    result["verdict"] = verdict(gate.get("exit"), exact, numbers)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {k: result.get(k) for k in ("exact", "numbers", "verdict")}, indent=1
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
