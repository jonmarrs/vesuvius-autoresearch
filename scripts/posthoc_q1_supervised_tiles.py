"""POST HOC (not registered): finding 76 Q1 on supervised tiles.

The registered Q1 re-analysis (2048-px windows with >= 25% supervised) found no qualifying windows, because
villa's supervision covers <= 13% of each segment. This asks the same question where the labels exist:
256-px tiles that are >= 50% mesh-valid AND supervised. Spearman rho of scorer fg density (what
total_fg_pixels counts) and of strip density against label density, bootstrap over segments (seed 20261004).

Usage: .venv/bin/python scripts/posthoc_q1_supervised_tiles.py [--out reports/posthoc_q1_supervised_tiles.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import stats

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkagree/src")
from inkagree.compare import domain_mask  # noqa: E402
from inkagree.labels import fetch_labels, fetch_supervision  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
W = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp/scorer_study")
TILE, MIN_FRAC, SEED, N_BOOT = 256, 0.5, 20261004, 2000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/posthoc_q1_supervised_tiles.json")
    )
    args = ap.parse_args()
    segs = sorted(p.name for p in W.iterdir() if p.is_dir() and p.name.startswith("20"))
    tiles = []
    for seg in segs:
        d = W / seg
        mask = (
            np.asarray(Image.open(d / "linear/ink_metric/predictions/seg_mask.png")) > 0
        )
        strip = np.asarray(Image.open(d / "linear/meshes/ink/seg.jpg"))
        lab, sup = fetch_labels(seg, 3), fetch_supervision(seg, 3)
        H = min(a.shape[0] for a in (mask, strip, lab, sup))
        Wd = min(a.shape[1] for a in (mask, strip, lab, sup))
        dom = domain_mask(d / "mesh/x.tif", mask.shape)[:H, :Wd] & sup[:H, :Wd]
        mask, strip, lab = mask[:H, :Wd], strip[:H, :Wd], lab[:H, :Wd]
        for y in range(0, H - TILE + 1, TILE):
            for x in range(0, Wd - TILE + 1, TILE):
                dd = dom[y : y + TILE, x : x + TILE]
                if dd.mean() < MIN_FRAC:
                    continue
                sl = (slice(y, y + TILE), slice(x, x + TILE))
                tiles.append({"segment": seg, "y": y, "x": x,
                              "scorer_density": float(mask[sl][dd].mean()),
                              "strip_density": float(strip[sl][dd].mean()) / 255,
                              "label_density": float(lab[sl][dd].mean())})  # fmt: skip
    rng = np.random.default_rng(SEED)
    segs_t = sorted({str(t["segment"]) for t in tiles})
    idx = {s: [i for i, t in enumerate(tiles) if t["segment"] == s] for s in segs_t}
    y = np.array([t["label_density"] for t in tiles])
    res = {"n_tiles": len(tiles), "tiles_per_segment": {s: len(idx[s]) for s in segs_t}}
    for key in ("scorer_density", "strip_density"):
        x = np.array([t[key] for t in tiles])
        rho = float(stats.spearmanr(x, y).statistic)
        boot = []
        for _ in range(N_BOOT):
            ii = [
                i
                for s in rng.choice(segs_t, size=len(segs_t), replace=True)
                for i in idx[s]
            ]
            boot.append(stats.spearmanr(x[ii], y[ii]).statistic)
        res[key] = {
            "rho": rho,
            "ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        }
    args.out.write_text(
        json.dumps({"post_hoc": True, **res, "tiles": tiles}, indent=2) + "\n"
    )
    print(
        f"n tiles {res['n_tiles']} across {len(segs_t)} segments: {res['tiles_per_segment']}"
    )
    for key in ("scorer_density", "strip_density"):
        print(
            f"  {key} vs label density: rho {res[key]['rho']:+.3f} [{res[key]['ci'][0]:+.3f}, {res[key]['ci'][1]:+.3f}]"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
