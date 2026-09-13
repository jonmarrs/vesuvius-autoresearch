"""Do different fits recover the same ink, or just the same AMOUNT of ink?

villa's spiral loop optimises `total_fg_pixels`, a COUNT. Every ablation we have
run returns null on that count -- but a count is silent about placement. If two
fits recover 2.9M ink pixels in different parts of the scroll, the number is
stable while the reading is not, and optimising the count would not be optimising
reading.

This compares the along-strip ink PROFILE between fits: for each arm, the ink
pixel count per column of the flattened strip, summed over rows.

Two facts about the artifacts shape the method:

* the prediction masks tile the strip HORIZONTALLY in 16384-wide chunks (the last
  is short), so a profile has to be concatenated across tiles;
* neither axis is constant between arms -- strips differ in both height and total
  width, because each fit produces its own flattening.

So profiles are compared at RELATIVE position (resampled to a common length) and
by CROSS-CORRELATION over a lag window, which absorbs a uniform shift. Without the
lag search a mere translation would look like disagreement.

What the numbers mean, and the limit of the method: a high correlation shows the
arms put ink in the same relative places. A LOW correlation is ambiguous -- it
could be genuine disagreement or a non-uniform stretch between flattenings that a
single lag cannot absorb. So this can confirm agreement but cannot, on its own,
prove disagreement.
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

try:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
except ImportError:  # pragma: no cover
    Image = None

COMMON = 8192  # resample length; well under the ~90k native width


def tile_index(path: str) -> int:
    """Masks are named ...mask.NNN.png and must be concatenated in that order."""
    return int(Path(path).stem.split(".")[-1])


def profile(arm_dir: str) -> np.ndarray | None:
    """Ink pixels per column across the whole strip, tiles concatenated in order."""
    fs = sorted(
        glob.glob(f"{arm_dir}/ink_metric/predictions/*mask*.png"), key=tile_index
    )
    if not fs:
        return None
    parts = []
    for f in fs:
        a = np.array(Image.open(f))
        parts.append((a > 127).sum(axis=0).astype(np.int64))
    return np.concatenate(parts)


def resample(p: np.ndarray, n: int = COMMON) -> np.ndarray:
    """Relative-position resample. Arms differ in total width, so absolute
    columns are not comparable."""
    x = np.linspace(0.0, 1.0, len(p))
    return np.interp(np.linspace(0.0, 1.0, n), x, p.astype(np.float64))


def best_correlation(a: np.ndarray, b: np.ndarray, max_lag: int = 256):
    """Max Pearson r over integer lags, with the lag that achieves it.

    A uniform offset between two flattenings would otherwise read as
    disagreement; the lag search removes that specific artefact and nothing else.
    """
    a = (a - a.mean()) / (a.std() or 1.0)
    b = (b - b.mean()) / (b.std() or 1.0)
    best, best_lag = -2.0, 0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            x, y = a[-lag:], b[: len(b) + lag]
        elif lag > 0:
            x, y = a[: len(a) - lag], b[lag:]
        else:
            x, y = a, b
        if len(x) < 100:
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if r > best:
            best, best_lag = r, lag
    return best, best_lag


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    if Image is None:
        raise SystemExit("needs Pillow")

    profs, meta = {}, {}
    for tag in args.arms:
        p = profile(f"{args.spiral_out}/outer_{tag}")
        if p is None:
            print(f"{tag}: no prediction masks, skipped")
            continue
        profs[tag] = resample(p)
        meta[tag] = {"native_width": int(len(p)), "total_fg": int(p.sum())}
        print(f"{tag:<20} width {len(p):>7,}  fg {int(p.sum()):>10,}")

    tags = list(profs)
    if len(tags) < 2:
        raise SystemExit("need at least two arms with masks")

    print(
        f"\npairwise max correlation of the along-strip ink profile (lag <= 256 of {COMMON})"
    )
    print(f"{'pair':<44}{'r':>8}{'lag':>7}")
    rows = []
    for i, a in enumerate(tags):
        for b in tags[i + 1 :]:
            r, lag = best_correlation(profs[a], profs[b])
            rows.append({"a": a, "b": b, "r": r, "lag": lag})
            print(f"{a + ' vs ' + b:<44}{r:>8.3f}{lag:>7}")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"common_length": COMMON, "arms": meta, "pairs": rows}, indent=1)
            + "\n"
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
