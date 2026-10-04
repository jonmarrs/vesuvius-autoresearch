"""docs/preregistration/2026-10-04_scorer_tracking_gap_robustness.md -- within villa's supervised regions, does the
rendered strip track labelled-ink density better than villa's scorer count, across render conditions and tile sizes?

Usage: .venv/bin/python scripts/scorer_tracking_gap.py [--out reports/scorer_tracking_gap.json]
"""

from __future__ import annotations

import argparse
import functools
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
G = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp")
SEGS = (
    "20230702185753 20230929220926 20231007101619 20231012184424 "
    "20231016151002 20231031143852 20231106155351 20231210121321"
).split()
ARMS = {  # name -> (study dir, mode); the first is the post-hoc reference
    "reference_f72_linear": ("scorer_study", "linear"),
    "f72_smooth": ("scorer_study", "smooth"),
    "f73_coarse_linear": ("scorer_study_coarse", "linear"),
    "f73_coarse_smooth": ("scorer_study_coarse", "smooth"),
}
TILES, MIN_FRAC, SEED, N_BOOT = (128, 256, 512), 0.5, 20261004, 2000


@functools.cache
def lab_sup(seg: str) -> tuple[np.ndarray, np.ndarray]:
    sup = fetch_supervision(seg, 3)
    if sup is None:
        raise RuntimeError(f"{seg}: no supervision mask")
    return fetch_labels(seg, 3), sup


def tiles_for(study: str, mode: str, tile: int) -> list[dict]:
    out = []
    for seg in SEGS:
        d = G / study / seg
        mask = (
            np.asarray(Image.open(d / mode / "ink_metric/predictions/seg_mask.png")) > 0
        )
        strip = np.asarray(Image.open(d / mode / "meshes/ink/seg.jpg"))
        lab, sup = lab_sup(seg)
        H = min(a.shape[0] for a in (mask, strip, lab, sup))
        W = min(a.shape[1] for a in (mask, strip, lab, sup))
        dom = domain_mask(d / "mesh/x.tif", mask.shape)[:H, :W] & sup[:H, :W]
        for y in range(0, H - tile + 1, tile):
            for x in range(0, W - tile + 1, tile):
                dd = dom[y : y + tile, x : x + tile]
                if dd.mean() < MIN_FRAC:
                    continue
                sl = (slice(y, y + tile), slice(x, x + tile))
                out.append({"segment": seg, "scorer": float(mask[:H, :W][sl][dd].mean()),
                            "strip": float(strip[:H, :W][sl][dd].mean()) / 255,
                            "label": float(lab[:H, :W][sl][dd].mean())})  # fmt: skip
    return out


def rho_ci(rows: list[dict], key: str, rng: np.random.Generator) -> dict:
    x = np.array([r[key] for r in rows])
    y = np.array([r["label"] for r in rows])
    segs = sorted({str(r["segment"]) for r in rows})
    idx = {s: [i for i, r in enumerate(rows) if r["segment"] == s] for s in segs}
    boot = []
    for _ in range(N_BOOT):
        ii = [i for s in rng.choice(segs, size=len(segs), replace=True) for i in idx[s]]
        boot.append(stats.spearmanr(x[ii], y[ii]).statistic)
    return {"rho": float(stats.spearmanr(x, y).statistic),
            "ci": [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))]}  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/scorer_tracking_gap.json")
    )
    args = ap.parse_args()
    cells = []
    for name, (study, mode) in ARMS.items():
        for tile in TILES:
            rows = tiles_for(study, mode, tile)
            rng = np.random.default_rng(SEED)
            s, c = rho_ci(rows, "strip", rng), rho_ci(rows, "scorer", rng)
            cells.append({"arm": name, "tile": tile, "n_tiles": len(rows), "strip": s, "scorer": c,
                          "gap": s["rho"] - c["rho"]})  # fmt: skip
            print(f"{name:22s} tile {tile:3d}: n {len(rows):4d}  strip rho {s['rho']:+.3f} "
                  f"[{s['ci'][0]:+.2f},{s['ci'][1]:+.2f}]  scorer rho {c['rho']:+.3f} "
                  f"[{c['ci'][0]:+.2f},{c['ci'][1]:+.2f}]  gap {s['rho'] - c['rho']:+.3f}")  # fmt: skip
    new = [c for c in cells if c["arm"] != "reference_f72_linear"]
    pred = {
        "p1_gap_ge_0.3_at_256_in_each_new_arm": all(
            c["gap"] >= 0.3 for c in new if c["tile"] == 256
        ),
        "p2_strip_gt_scorer_in_all_9_new_cells": all(c["gap"] > 0 for c in new),
    }
    args.out.write_text(
        json.dumps({"cells": cells, "predictions_held": pred}, indent=2) + "\n"
    )
    print("predictions held:", pred)
    return 0


if __name__ == "__main__":
    sys.exit(main())
