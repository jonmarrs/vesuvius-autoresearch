"""docs/preregistration/2026-10-04_objective_vs_labels.md -- does villa's ink-count objective track villa's labels?

Q1: Spearman rho, across 2048-px windows, of the scorer's fg density (the pixels total_fg_pixels counts) and of
    the strip's mean intensity, against labelled-ink density; bootstrap over segments.
Q2: AP of the scorer probability and of the strip against labels dilated by r px; their ratio.

Usage: .venv/bin/python scripts/analyse_objective_vs_labels.py [--out reports/objective_vs_labels.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage, stats

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkagree/src")
from inkagree.compare import domain_mask  # noqa: E402
from inkagree.metrics import metrics_from_hist  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
W = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp/scorer_study")
WIN, MIN_DOMAIN, SEED, N_BOOT = 2048, 0.25, 20261004, 2000
DILATIONS = (0, 1, 2, 4, 8)


def load(seg: str) -> dict:
    d = W / seg
    lab = np.load(d / "labels_L3.npy") > 127
    pred = d / "linear/ink_metric/predictions"
    mask = np.asarray(Image.open(pred / "seg_mask.png")) > 0
    prob = np.load(pred / "seg_flat_prob.npy").astype(np.float32)
    strip = np.asarray(Image.open(d / "linear/meshes/ink/seg.jpg"))
    dom_full = domain_mask(d / "mesh" / "x.tif", mask.shape)
    H, W_ = (
        min(a.shape[0] for a in (lab, mask, strip)),
        min(a.shape[1] for a in (lab, mask, strip)),
    )
    c = lambda a: a[:H, :W_]  # noqa: E731
    q = np.clip(np.rint(prob * 255), 0, 255).astype(np.uint8)
    return {
        "lab": c(lab),
        "mask": c(mask),
        "prob_q": c(q),
        "strip": c(strip),
        "dom": c(dom_full),
    }


def windows(seg: str, a: dict) -> list[dict]:
    out = []
    H, W_ = a["lab"].shape
    for x0 in range(0, W_ - WIN + 1, WIN):
        sl = (slice(None), slice(x0, x0 + WIN))
        dom = a["dom"][sl]
        n = int(dom.sum())
        if n < MIN_DOMAIN * dom.size:
            continue
        out.append({
            "segment": seg, "x0": x0, "domain_px": n,
            "scorer_density": float(a["mask"][sl][dom].mean()),
            "label_density": float(a["lab"][sl][dom].mean()),
            "strip_density": float(a["strip"][sl][dom].mean()) / 255.0,
        })  # fmt: skip
    return out


def rho_with_ci(rows: list[dict], key: str, rng: np.random.Generator) -> dict:
    x = np.array([r[key] for r in rows])
    y = np.array([r["label_density"] for r in rows])
    rho = float(stats.spearmanr(x, y).statistic)
    segs = sorted({r["segment"] for r in rows})
    idx = {s: [i for i, r in enumerate(rows) if r["segment"] == s] for s in segs}
    boot = []
    for _ in range(N_BOOT):
        pick = rng.choice(segs, size=len(segs), replace=True)
        ii = [i for s in pick for i in idx[s]]
        if len(set(x[ii])) > 1 and len(set(y[ii])) > 1:
            boot.append(stats.spearmanr(x[ii], y[ii]).statistic)
    return {
        "rho": rho,
        "ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "n": len(rows),
    }


def q2(data: dict[str, dict]) -> list[dict]:
    out = []
    for r in DILATIONS:
        hs = {
            "prob_q": [np.zeros(256), np.zeros(256)],
            "strip": [np.zeros(256), np.zeros(256)],
        }
        for a in data.values():
            lab = ndimage.binary_dilation(a["lab"], iterations=r) if r else a["lab"]
            dom = a["dom"]
            for k in hs:
                s = a[k]
                hs[k][0] += np.bincount(s[dom & lab], minlength=256)
                hs[k][1] += np.bincount(s[dom & ~lab], minlength=256)
        ap_s = metrics_from_hist(*hs["prob_q"])["ap"]
        ap_t = metrics_from_hist(*hs["strip"])["ap"]
        out.append(
            {
                "dilation_px": r,
                "ap_scorer": ap_s,
                "ap_strip": ap_t,
                "ratio": ap_s / ap_t,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/objective_vs_labels.json")
    )
    args = ap.parse_args()
    segs = sorted(p.name for p in W.iterdir() if p.is_dir() and p.name.startswith("20"))
    data = {s: load(s) for s in segs}
    rows = [w for s in segs for w in windows(s, data[s])]
    rng = np.random.default_rng(SEED)
    q1 = {
        "scorer": rho_with_ci(rows, "scorer_density", rng),
        "strip": rho_with_ci(rows, "strip_density", rng),
    }
    q2r = q2(data)
    pred = {
        "p1_scorer_rho_gt_0.3_ci_excludes_0": q1["scorer"]["rho"] > 0.3
        and q1["scorer"]["ci"][0] > 0,
        "p2_strip_rho_ge_scorer_rho": q1["strip"]["rho"] >= q1["scorer"]["rho"],
        "p3_ratio_rises_and_r8_gt_r0": all(
            b["ratio"] >= a["ratio"] for a, b in zip(q2r, q2r[1:], strict=False)
        )
        and q2r[-1]["ratio"] > q2r[0]["ratio"],
    }
    res = {
        "segments": segs,
        "windows": rows,
        "q1": q1,
        "q2": q2r,
        "predictions_held": pred,
    }
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    print(f"Q1 (n = {q1['scorer']['n']} windows, 8 segments):")
    for k in ("scorer", "strip"):
        print(
            f"  {k:6s} density vs label density: rho {q1[k]['rho']:+.3f}  [{q1[k]['ci'][0]:+.3f}, {q1[k]['ci'][1]:+.3f}]"
        )
    print("Q2 (labels dilated by r px at 19.2 um/px):")
    for r in q2r:
        print(
            f"  r={r['dilation_px']}: AP scorer {r['ap_scorer']:.4f}  strip {r['ap_strip']:.4f}  ratio {r['ratio']:.3f}"
        )
    print("predictions held:", pred)
    return 0


if __name__ == "__main__":
    sys.exit(main())
