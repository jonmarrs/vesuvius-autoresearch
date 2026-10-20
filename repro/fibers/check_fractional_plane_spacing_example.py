"""Check Villa's seed-plane placement on one published Scroll-1 mask.

Run as ``python -m repro.fibers.check_fractional_plane_spacing_example
--volume VILLA/volume.py --mask seeding-data/s1_mask.npz``. Returns 1 for
the known misplaced planes on baseline and 0 for the corrected placement.
This invokes the source file's CPU seed functions, without model inference.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from repro.fibers.check_fractional_plane_spacing import MASKS, load_seeding, presence_from_mask, sha256


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--volume", type=Path, required=True, help="Villa tracing/volume.py to check")
    ap.add_argument("--mask", type=Path, required=True, help="ScrollGT v0.8.1's published Scroll-1 mask")
    args = ap.parse_args()
    cube, expected_hash = MASKS["s1"]
    if sha256(args.mask) != expected_hash:
        raise ValueError("Input is not the published ScrollGT v0.8.1 Scroll-1 mask")
    shape, presence = presence_from_mask(args.mask)
    spacing = 64*7.91/9.6
    settings = SimpleNamespace(threshold=128., dot_radius=2., fill_spacing=4., plane_spacing=spacing)
    dots = load_seeding(args.volume).tile_dots(
        presence, np.zeros(3), np.array(presence.shape[::-1], float), settings
    )
    planes = [] if dots is None else sorted({int(p[1:]) for p in dots["plane"] if p.startswith("z")})
    print(f"Cube: {cube}; mask shape: {shape}")
    print(f"Presence: {presence.shape}; plane spacing: {spacing:.9f} grid voxels")
    print("Observed z planes: " + ", ".join(map(str, planes)))
    print("Expected z planes: 0, 52, 105")
    print(f"Seed dots: {0 if dots is None else len(dots['xyz'])}")
    valid = planes == [0, 52, 105]
    print("PASS: global plane placement" if valid else "FAIL: planes drift from the requested global spacing")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
