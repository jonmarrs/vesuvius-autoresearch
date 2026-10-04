"""DESCRIPTIVE (not registered): checks run after scripts/scorer_tracking_gap.py, to bound how far its registered result
can be read. Not predictions; nothing here changes the registered verdict.

1. Paired bootstrap of the gap itself (strip rho - scorer rho), resampling segments, reference arm.
2. Does the scorer's probability (mean, before villa's 0.5 threshold) track label density better than its count?
3. Within-segment rho: is the pooled rho driven by differences between segments?
4. How independent are the "new" arms: per-tile correlation of each arm's densities with the reference's.

Usage: .venv/bin/python scripts/scorer_tracking_gap_descriptive.py [--out reports/scorer_tracking_gap_descriptive.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scorer_tracking_gap import (  # noqa: E402
    ARMS,
    MIN_FRAC,
    N_BOOT,
    SEED,
    SEGS,
    TILES,
    G,
    lab_sup,
)

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkagree/src")
from inkagree.compare import domain_mask  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def tiles_with_prob(study: str, mode: str, tile: int) -> list[dict]:
    out = []
    for seg in SEGS:
        d = G / study / seg / mode
        prob = np.load(d / "ink_metric/predictions/seg_flat_prob.npy").astype(
            np.float32
        )
        mask = np.asarray(Image.open(d / "ink_metric/predictions/seg_mask.png")) > 0
        strip = np.asarray(Image.open(d / "meshes/ink/seg.jpg"))
        lab, sup = lab_sup(seg)
        H = min(a.shape[0] for a in (prob, mask, strip, lab, sup))
        W = min(a.shape[1] for a in (prob, mask, strip, lab, sup))
        dom = (
            domain_mask(G / study / seg / "mesh/x.tif", mask.shape)[:H, :W]
            & sup[:H, :W]
        )
        for y in range(0, H - tile + 1, tile):
            for x in range(0, W - tile + 1, tile):
                dd = dom[y : y + tile, x : x + tile]
                if dd.mean() < MIN_FRAC:
                    continue
                sl = (slice(y, y + tile), slice(x, x + tile))
                out.append({"segment": seg, "y": y, "x": x,
                            "scorer": float(mask[:H, :W][sl][dd].mean()),
                            "prob": float(prob[:H, :W][sl][dd].mean()),
                            "strip": float(strip[:H, :W][sl][dd].mean()) / 255,
                            "label": float(lab[:H, :W][sl][dd].mean())})  # fmt: skip
    return out


def rho(rows: list[dict], a: str, b: str = "label") -> float:
    return float(stats.spearmanr([r[a] for r in rows], [r[b] for r in rows]).statistic)


def gap_ci(rows: list[dict], a: str, b: str) -> dict:
    rng = np.random.default_rng(SEED)
    by = {
        s: [r for r in rows if r["segment"] == s]
        for s in sorted({r["segment"] for r in rows})
    }
    segs = list(by)
    boot = []
    for _ in range(N_BOOT):
        rr = [r for s in rng.choice(segs, size=len(segs), replace=True) for r in by[s]]
        boot.append(rho(rr, a) - rho(rr, b))
    return {"gap": rho(rows, a) - rho(rows, b),
            "ci": [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))]}  # fmt: skip


def within_segment(rows: list[dict]) -> dict:
    out = {}
    for s in sorted({r["segment"] for r in rows}):
        rr = [r for r in rows if r["segment"] == s]
        out[s] = {"n": len(rr), **{k: rho(rr, k) for k in ("strip", "scorer", "prob")}}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/scorer_tracking_gap_descriptive.json")
    )
    args = ap.parse_args()
    res: dict = {"registered": False, "reference": {}, "arm_independence_256": {}}
    ref_study, ref_mode = ARMS["reference_f72_linear"]
    for tile in TILES:
        rows = tiles_with_prob(ref_study, ref_mode, tile)
        ws = within_segment(rows)
        res["reference"][tile] = {
            "n_tiles": len(rows),
            "rho": {k: rho(rows, k) for k in ("strip", "scorer", "prob")},
            "rho_scorer_vs_its_input": rho(rows, "scorer", "strip"),
            "gap_strip_minus_scorer": gap_ci(rows, "strip", "scorer"),
            "gap_strip_minus_prob": gap_ci(rows, "strip", "prob"),
            "within_segment": ws,
            "within_segment_median": {
                k: float(np.median([v[k] for v in ws.values() if v["n"] >= 5]))
                for k in ("strip", "scorer", "prob")
            },
        }
        r = res["reference"][tile]
        g = r["gap_strip_minus_scorer"]
        print(f"tile {tile}: n {len(rows)}  rho strip {r['rho']['strip']:+.3f} scorer {r['rho']['scorer']:+.3f} "
              f"prob {r['rho']['prob']:+.3f}  gap {g['gap']:+.3f} [{g['ci'][0]:+.2f},{g['ci'][1]:+.2f}]  "
              f"scorer~strip {r['rho_scorer_vs_its_input']:+.3f}")  # fmt: skip
        print("   within-segment median (segments with >= 5 tiles):", {k: round(v, 3) for k, v in r["within_segment_median"].items()})  # fmt: skip
        for s, v in ws.items():
            print(f"   {s}: n {v['n']:4d}  strip {v['strip']:+.3f}  scorer {v['scorer']:+.3f}  prob {v['prob']:+.3f}")  # fmt: skip
    ref = tiles_with_prob(ref_study, ref_mode, 256)
    for name, (study, mode) in ARMS.items():
        if name == "reference_f72_linear":
            continue
        rows = tiles_with_prob(study, mode, 256)
        assert [(r["segment"], r["y"], r["x"]) for r in rows] == [
            (r["segment"], r["y"], r["x"]) for r in ref
        ]
        res["arm_independence_256"][name] = {
            k: float(
                stats.pearsonr([a[k] for a in ref], [b[k] for b in rows]).statistic
            )
            for k in ("strip", "scorer")
        }
        print(f"{name}: per-tile r with reference  {res['arm_independence_256'][name]}")
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
