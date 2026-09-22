"""Build one arm of the scorer-translation study: a source strip, offset by (dy, dx).

`docs/preregistration/2026-09-22_scorer_translation.md`. The strip is decoded ONCE
exactly as `get_ink_metrics.load_concat_strip` decodes it (8-bit L, short tiles
padded at the bottom, tiles concatenated along x), padded with black on the top
and left, and written as ONE lossless PNG. Every source pixel survives unchanged;
only position and canvas size change. Re-encoding as JPEG would confound the shift
with compression, which is why the output is PNG (the scorer accepts it).

Usage:
    build_shifted_strip_arm.py <src ink dir> <out arm dir> --dx N --dy N
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
NAME = "w120-129_flat"


def load_strip(ink_dir: Path) -> np.ndarray:
    tiles = sorted(
        (
            p
            for p in Path(ink_dir).iterdir()
            if p.suffix.lower() == ".jpg" and "_flat" in p.name
        ),
        key=lambda p: int(re.match(r"^.*\.(\d+)$", p.stem).group(1)),
    )
    if not tiles:
        raise SystemExit(f"no _flat jpg tiles in {ink_dir}")
    arrs = [np.asarray(Image.open(p).convert("L")) for p in tiles]
    h = max(a.shape[0] for a in arrs)
    arrs = [
        a if a.shape[0] == h else np.pad(a, ((0, h - a.shape[0]), (0, 0))) for a in arrs
    ]
    return np.concatenate(arrs, axis=1)


def build(src_ink: Path, out_ink: Path, dx: int, dy: int) -> Path:
    s = load_strip(src_ink)
    shifted = np.pad(s, ((dy, 0), (dx, 0)))
    out_ink = Path(out_ink)
    out_ink.mkdir(parents=True, exist_ok=True)
    p = out_ink / f"{NAME}.png"
    Image.fromarray(shifted).save(p, optimize=False, compress_level=1)
    back = np.asarray(Image.open(p))
    if not np.array_equal(back[dy:, dx:], s):
        raise SystemExit(
            f"round-trip mismatch in {p}: the PNG does not hold the source pixels"
        )
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "src_arm", help="scored arm whose meshes/ink/*.jpg is the source strip"
    )
    ap.add_argument("out_arm")
    ap.add_argument("--dx", type=int, required=True)
    ap.add_argument("--dy", type=int, required=True)
    a = ap.parse_args()
    src, out = Path(a.src_arm), Path(a.out_arm)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite")
    p = build(src / "meshes" / "ink", out / "meshes" / "ink", a.dx, a.dy)
    # the scorer runs from <arm>/spiral-fitting; give each arm its own copy of the source's
    shutil.copytree(src / "spiral-fitting", out / "spiral-fitting", symlinks=True)
    for f in ("VILLA_SHA", "RENDER_IMAGE"):
        if (src / f).exists():
            shutil.copy2(src / f, out / f)
    (out / "SHIFT").write_text(f"dx={a.dx} dy={a.dy} src={src}\n")
    print(
        f"built {out}: {p.name} shifted dx={a.dx} dy={a.dy}, {os.path.getsize(p):,} bytes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
