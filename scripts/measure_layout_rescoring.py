"""Is an ink-score difference between two scored arms AREA, DENSITY, and how LOCAL is it?

For two arms that render the same surface laid out differently (for example two stock
flattens of identical meshes), this separates:

* **area**: how many strip pixels the sheet covers (strip value > 8), and
* **density**: ink pixels (scorer mask > 0) per covered pixel,

then splits the ink change into blocks along the strip. It reports the ink-weighted
spread per block, the lag-1 correlation between neighbouring blocks, the spread
independent blocks would imply for the total, and how the spread falls with block width.

Reads `meshes/ink/w120-129_flat.NNN.*` and `ink_metric/predictions/*_mask.NNN.png`
tile by tile, so memory stays at one tile. See
`reports/the_flatten_noise_is_local_rescoring.md`.

Run:
    python scripts/measure_layout_rescoring.py <arm A> <arm B> [--json out]
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BLOCKS = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
COVER_T = 8


def _idx(p: Path) -> int:
    m = re.search(r"\.(\d+)$", p.stem)
    return int(m.group(1)) if m else -1


def _columns(arm: Path) -> tuple[np.ndarray, np.ndarray]:
    """Per-column covered-pixel and ink-pixel counts along the whole strip."""
    strips = sorted(
        (p for p in (arm / "meshes" / "ink").iterdir() if "_flat" in p.name),
        key=_idx,
    )
    masks = sorted((arm / "ink_metric" / "predictions").glob("*_mask*.png"), key=_idx)
    if len(strips) != len(masks):
        raise SystemExit(f"{arm}: {len(strips)} strip tiles vs {len(masks)} mask tiles")
    cov, fg = [], []
    for s, m in zip(strips, masks, strict=True):
        a = np.asarray(Image.open(s).convert("L"))
        k = np.asarray(Image.open(m))
        k = k[..., 0] if k.ndim == 3 else k
        cov.append((a > COVER_T).sum(0))
        fg.append((k > 0).sum(0))
    return np.concatenate(cov).astype(float), np.concatenate(fg).astype(float)


def _block(fa: np.ndarray, fb: np.ndarray, B: int) -> dict[str, float | int | None]:
    n = min(len(fa), len(fb)) // B
    ba = fa[: n * B].reshape(n, B).sum(1)
    bb = fb[: n * B].reshape(n, B).sum(1)
    ok = ba > 0
    d = (bb[ok] - ba[ok]) / ba[ok]
    w = ba[ok] / ba[ok].sum()
    sd = float(np.sqrt(np.average((d - np.average(d, weights=w)) ** 2, weights=w)))
    # undefined (None) when either side of the neighbour pair has no variance
    lag = (
        float(np.corrcoef(d[:-1], d[1:])[0, 1])
        if len(d) > 2 and d[:-1].std() > 0 and d[1:].std() > 0
        else None
    )
    return {
        "n": int(ok.sum()),
        "sd": sd,
        "sd_scaled_to_2048": sd * float(np.sqrt(B / 2048)),
        "lag1": lag,
        "implied_total_sd": sd * float(np.sqrt((w**2).sum())),
        "blocks_losing": int((d < 0).sum()),
    }


def compare(arm_a, arm_b, blocks=BLOCKS) -> dict:
    ca, fa = _columns(Path(arm_a))
    cb, fb = _columns(Path(arm_b))
    cov_r = float(cb.sum() / ca.sum())
    fg_r = float(fb.sum() / fa.sum())
    return {
        "covered_ratio": cov_r,
        "fg_ratio": fg_r,
        "density_ratio": fg_r / cov_r,
        "block": {B: _block(fa, fb, B) for B in blocks},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    r = compare(a.a, a.b)
    print(f"A {a.a}\nB {a.b}")
    print(
        f"  covered area B/A {r['covered_ratio']:.4f}   ink B/A {r['fg_ratio']:.4f}"
        f"   density B/A {r['density_ratio']:.4f}"
    )
    print(
        f"  {'block':>6}{'n':>5}{'sd':>9}{'sd@2048':>9}{'lag1':>7}{'implied total':>15}{'losing':>8}"
    )
    for B, s in r["block"].items():
        print(
            f"  {B:>6}{s['n']:>5}{s['sd']:>9.4f}{s['sd_scaled_to_2048']:>9.4f}"
            f"{'n/a' if s['lag1'] is None else format(s['lag1'], '+.2f'):>7}"
            f"{s['implied_total_sd']:>15.4f}{s['blocks_losing']:>8}"
        )
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
