"""Is the ink scorer sensitive to WHERE a strip sits on its canvas?

Implements `docs/preregistration/2026-09-22_scorer_translation.md`. **Written
before any arm was built.**

Two stock flattens of identical meshes lie on the same surface (0.25 vx along the
normal) and cover the same strip area to 0.2%, yet score 3.04% apart -- all of it
ink DENSITY. The scorer is an nnU-Net 2d sliding window (768 x 2048 patch, 50%
overlap). This asks whether moving one fixed strip by a few pixels, which moves
the tile grid over the content and nothing else, moves `total_fg_pixels`.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SRC = "radial_work_rad0"  # the source strip; scored from its jpg tiles: 1,698,831
ARMS = {  # name -> (dx, dy)
    "stx_d0a": (0, 0),
    "stx_d0b": (0, 0),
    "stx_x1": (1, 0),
    "stx_x2": (2, 0),
    "stx_x8": (8, 0),
    "stx_x64": (64, 0),
    "stx_x512": (512, 0),
    "stx_y1": (0, 1),
    "stx_y8": (0, 8),
    "stx_y64": (0, 64),
}
F_RECORDED = 24 / 1_698_831  # reports/holding_the_flatten_fixed_collapses_the_floor.md
MARGIN = 3.0
BIG = 0.01  # registered: >= 1% spread is layout-sensitive
INK = "total_fg_pixels"


# Per-block rescoring (descriptive). The rad0 vs rad0b reference was measured at
# BLOCK px: same surface re-laid-out, ink-weighted, 40 blocks.
BLOCK = 2048
REF_BLOCK_SD = 0.135


def _mask(pred_dir) -> np.ndarray:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    parts = []
    for p in sorted(Path(pred_dir).glob("*_mask*.png")):
        a = np.asarray(Image.open(p))
        parts.append((a[..., 0] if a.ndim == 3 else a) > 0)
    h = max(x.shape[0] for x in parts)
    parts = [np.pad(x, ((0, h - x.shape[0]), (0, 0))) for x in parts]
    return np.concatenate(parts, axis=1)


def block_sd(pred_a, pred_b, dx: int, dy: int, block: int = BLOCK) -> float:
    """Ink-weighted sd of the per-block relative change from prediction A (at the
    source position) to prediction B (offset by dy, dx), after undoing the offset.
    DESCRIPTIVE ONLY: it asks whether a pure shift reproduces the block-level
    rescoring seen between two layouts of the same surface; it is not in the verdict."""
    a = _mask(pred_a).sum(0).astype(float)
    b = _mask(pred_b)[dy:, dx:].sum(0).astype(float)
    n = min(len(a), len(b)) // block
    ba = a[: n * block].reshape(n, block).sum(1)
    bb = b[: n * block].reshape(n, block).sum(1)
    ok = ba > 0
    d = (bb[ok] - ba[ok]) / ba[ok]
    w = ba[ok] / ba[ok].sum()
    return float(np.sqrt(np.average((d - np.average(d, weights=w)) ** 2, weights=w)))


def verdict(spread: float, floor: float) -> tuple[str, str]:
    if spread >= BIG:
        return "LAYOUT-SENSITIVE", (
            "Moving a fixed strip moves the objective by >= 1%: part of total_fg_pixels is "
            "where the scorer's tiles fall, not what is on the sheet."
        )
    if spread >= MARGIN * floor:
        return "SENSITIVE, SMALL", (
            "Detectable above the scorer's repeat floor, but under 1%: it cannot account "
            "for most of the 3.04% between two flattens of the same surface."
        )
    return "INSENSITIVE", (
        "Translation does not move the score beyond the repeat floor; the 3.04% must come "
        "from the layout's local distortion, not its position."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)

    missing = [n for n in ARMS if not (so / n / "ink_metric" / "metrics.json").exists()]
    if missing:
        raise SystemExit(f"not scored: {', '.join(missing)} -- partial study refused.")
    v = {
        n: json.loads((so / n / "ink_metric" / "metrics.json").read_text())["summary"][
            INK
        ]
        for n in ARMS
    }
    src = json.loads((so / SRC / "ink_metric" / "metrics.json").read_text())["summary"][
        INK
    ]

    base = (v["stx_d0a"] + v["stx_d0b"]) / 2
    repeat = abs(v["stx_d0a"] - v["stx_d0b"]) / base
    floor = max(repeat, F_RECORDED)
    spread = (max(v.values()) - min(v.values())) / (sum(v.values()) / len(v))

    print("SCORER TRANSLATION: one fixed strip, offset on its canvas\n")
    print(f"  {'arm':<10}{'dx':>5}{'dy':>5}{'total_fg':>12}{'vs d0':>10}")
    for n, (dx, dy) in ARMS.items():
        print(f"  {n:<10}{dx:>5}{dy:>5}{v[n]:>12,}{(v[n] - base) / base:>+10.4%}")
    print(
        f"\n  repeat floor (d0a vs d0b) {repeat:.5%}; recorded floor {F_RECORDED:.5%}; used {floor:.5%}"
    )
    print(
        f"  pipeline check: PNG d0 vs the source's JPEG score {src:,}: {(base - src) / src:+.5%}"
    )
    print(f"  spread (max - min) / mean over all arms: {spread:.4%}")
    print(
        f"\n  DESCRIPTIVE (not in the verdict): per-block sd vs stx_d0a, {BLOCK}-px blocks;"
        f" reference rad0b vs rad0 = {REF_BLOCK_SD:.3f}"
    )
    bsd = {}
    for n, (dx, dy) in ARMS.items():
        if n == "stx_d0a":
            continue
        bsd[n] = block_sd(
            so / "stx_d0a" / "ink_metric" / "predictions",
            so / n / "ink_metric" / "predictions",
            dx,
            dy,
        )
        print(f"    {n:<10} {bsd[n]:.4f}")
    name, read = verdict(spread, floor)
    print(f"\nVERDICT: {name}\n  {read}")
    print(
        "  For scale: two flattens of the same surface differ by 3.04% (rad0 vs rad0b)."
    )
    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {
                    "scores": v,
                    "source_jpeg": src,
                    "repeat": repeat,
                    "floor": floor,
                    "spread": spread,
                    "verdict": name,
                    "block_sd": bsd,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
