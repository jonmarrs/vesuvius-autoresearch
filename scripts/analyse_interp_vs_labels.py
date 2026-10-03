"""docs/preregistration/2026-10-03_surface_interpolation_vs_labels.md -- linear vs smooth renders of the 3D ink
prediction, scored against villa's published ink labels on 8 Scroll-1 segments.

    maxcomp OUT TIFDIR   max over the per-slice TIFFs in TIFDIR -> OUT (uint8 TIFF), slice by slice
    labels SEG OUT       fetch SEG's level-2 label raster (20260918) from the open-data bucket -> OUT (.npy)
    analyse [--out]      the registered metrics, alignment gate and block bootstrap
    selftest             histogram AP/AUC against scikit-learn on random data
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

WORK = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp/study")
BUCKET = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
LABEL_PATH = "PHercParis4/segments/{seg}/ink-labels/2.4um-volume-20260411134726/20260918/inklabels.zarr/2/"
SEGMENTS = (
    "20230702185753 20230929220926 20231007101619 20231012184424 "
    "20231016151002 20231031143852 20231106155351 20231210121321"
).split()
BLOCK, N_BOOT, SEED, SHIFT, GATE_TOL = 512, 2000, 20261003, 3, 1


# ----------------------------------------------------------------------------- metrics from histograms


def metrics_from_hist(pos: np.ndarray, neg: np.ndarray) -> dict:
    """AP, ROC-AUC and best F1 for integer scores 0..255, ties grouped (as scikit-learn does)."""
    tp = np.cumsum(pos[::-1].astype(np.float64))
    fp = np.cumsum(neg[::-1].astype(np.float64))
    P, N = tp[-1], fp[-1]
    if P == 0 or N == 0:
        return {"ap": float("nan"), "auc": float("nan"), "best_f1": float("nan")}
    keep = (tp + fp) > 0
    tp, fp = tp[keep], fp[keep]
    precision, recall = tp / (tp + fp), tp / P
    ap = float(np.sum(np.diff(np.concatenate([[0.0], recall])) * precision))
    tpr = np.concatenate([[0.0], recall])
    fpr = np.concatenate([[0.0], fp / N])
    auc = float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2))
    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-12)
    return {"ap": ap, "auc": auc, "best_f1": float(f1.max())}


# ----------------------------------------------------------------------------- inputs


def maxcomp(out: Path, tifdir: Path) -> None:
    fs = sorted(tifdir.glob("*.tif"))
    if len(fs) != 16:
        sys.exit(f"{tifdir}: {len(fs)} slices, expected 16")
    comp = None
    for f in fs:
        a = tifffile.imread(f)
        comp = a if comp is None else np.maximum(comp, a)
    assert comp is not None and comp.dtype == np.uint8
    tifffile.imwrite(out, comp, compression="zlib")
    print(f"maxcomp {out}: {comp.shape}")


def fetch_labels(seg: str, out: Path) -> None:
    import tensorstore as ts

    t = ts.open({"driver": "zarr3", "kvstore": {"driver": "http", "base_url": BUCKET,
                                                "path": LABEL_PATH.format(seg=seg)}}).result()  # fmt: skip
    a = t.read().result()
    assert a.dtype == np.uint8 and set(np.unique(a)) <= {0, 255}, (
        f"{seg}: labels not binary 0/255"
    )
    np.save(out, a)
    print(f"labels {seg}: {a.shape}, ink {float((a > 127).mean()):.4f}")


def domain_mask(mesh_x: Path, shape: tuple[int, int]) -> np.ndarray:
    """Canvas pixels whose source grid cell is valid (x != -1), nearest-upsampled to the canvas."""
    gx = tifffile.imread(mesh_x)
    valid = np.isfinite(gx) & (gx != -1)
    gh, gw = valid.shape
    H, W = shape
    ri = np.minimum((np.arange(H) * gh) // H, gh - 1)
    ci = np.minimum((np.arange(W) * gw) // W, gw - 1)
    return valid[np.ix_(ri, ci)]


# ----------------------------------------------------------------------------- per segment


def block_hists(
    score: np.ndarray, lab: np.ndarray, dom: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """(n_blocks, 256) positive and negative histograms, accumulated in 512-row strips."""
    H, W = score.shape
    nby, nbx = -(-H // BLOCK), -(-W // BLOCK)
    pos = np.zeros((nby * nbx, 256), np.int64)
    neg = np.zeros((nby * nbx, 256), np.int64)
    cols = np.arange(W) // BLOCK
    for by in range(nby):
        sl = slice(by * BLOCK, min(H, (by + 1) * BLOCK))
        s, ink, d = score[sl], lab[sl] > 127, dom[sl]
        idx = (by * nbx + np.broadcast_to(cols, s.shape)) * 256 + s.astype(np.int64)
        pos += np.bincount(idx[d & ink], minlength=nby * nbx * 256).reshape(-1, 256)
        neg += np.bincount(idx[d & ~ink], minlength=nby * nbx * 256).reshape(-1, 256)
    return pos, neg


def alignment_peak(score: np.ndarray, lab: np.ndarray, dom: np.ndarray) -> dict:
    """AUC of score vs labels shifted by (dy, dx) in [-SHIFT, SHIFT]^2, exact, on the central window of up
    to 4096 x 4096 canvas px (score[y, x] is compared with label[y + dy, x + dx])."""
    H, W = score.shape
    h, w = min(H - 2 * SHIFT, 4096), min(W - 2 * SHIFT, 4096)
    y0, x0 = (H - h) // 2, (W - w) // 2
    s, d = score[y0 : y0 + h, x0 : x0 + w], dom[y0 : y0 + h, x0 : x0 + w]
    out = {}
    for dy in range(-SHIFT, SHIFT + 1):
        for dx in range(-SHIFT, SHIFT + 1):
            ll = lab[y0 + dy : y0 + dy + h, x0 + dx : x0 + dx + w] > 127
            p = np.bincount(s[d & ll].ravel(), minlength=256)
            n = np.bincount(s[d & ~ll].ravel(), minlength=256)
            out[(dy, dx)] = metrics_from_hist(p, n)["auc"]
    (py, px), best = max(out.items(), key=lambda kv: kv[1])
    return {"peak_dy": py, "peak_dx": px, "peak_auc": best, "auc_at_0": out[(0, 0)],
            "window": [y0, x0, h, w], "passes": abs(py) <= GATE_TOL and abs(px) <= GATE_TOL}  # fmt: skip


def bootstrap(hl: tuple, hs: tuple, rng: np.random.Generator) -> dict:
    (pl, nl), (ps, ns) = hl, hs
    nb = pl.shape[0]
    occupied = np.flatnonzero((pl + nl).sum(1) > 0)
    d_ap, d_auc = [], []
    for _ in range(N_BOOT):
        w = np.bincount(
            rng.choice(occupied, size=len(occupied), replace=True), minlength=nb
        )
        ml = metrics_from_hist(w @ pl, w @ nl)
        ms = metrics_from_hist(w @ ps, w @ ns)
        d_ap.append(ms["ap"] - ml["ap"])
        d_auc.append(ms["auc"] - ml["auc"])
    q = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]  # noqa: E731
    return {"d_ap_ci": q(d_ap), "d_auc_ci": q(d_auc), "n_blocks": int(len(occupied))}


def analyse_segment(seg: str, rng: np.random.Generator) -> dict:
    d = WORK / seg
    lab = np.load(d / "labels_L2.npy")
    lin = tifffile.imread(d / "linear_max.tif")
    smo = tifffile.imread(d / "smooth_max.tif")
    row: dict = {"segment": seg, "shape": list(lab.shape)}
    if lin.shape != lab.shape or smo.shape != lab.shape:
        row["excluded"] = f"canvas {lin.shape}/{smo.shape} != labels {lab.shape}"
        return row
    dom = domain_mask(d / "mesh" / "x.tif", lab.shape)
    row["domain_px"] = int(dom.sum())
    row["label_ink_frac_in_domain"] = float((lab[dom] > 127).mean())
    gate = alignment_peak(lin, lab, dom)
    row["alignment"] = gate
    if not gate["passes"]:
        row["excluded"] = "alignment peak more than 1 px from (0, 0)"
        return row
    hl, hs = block_hists(lin, lab, dom), block_hists(smo, lab, dom)
    row["linear"] = metrics_from_hist(hl[0].sum(0), hl[1].sum(0))
    row["smooth"] = metrics_from_hist(hs[0].sum(0), hs[1].sum(0))
    row["d_ap"] = row["smooth"]["ap"] - row["linear"]["ap"]
    row["d_auc"] = row["smooth"]["auc"] - row["linear"]["auc"]
    row.update(bootstrap(hl, hs, rng))
    return row


def analyse(out: Path) -> int:
    rng = np.random.default_rng(SEED)
    rows = []
    for seg in SEGMENTS:
        r = analyse_segment(seg, rng)
        rows.append(r)
        if "excluded" in r:
            print(f"{seg}: EXCLUDED ({r['excluded']})")
            continue
        print(f"{seg}: AP {r['linear']['ap']:.4f} -> {r['smooth']['ap']:.4f}  dAP {r['d_ap']:+.4f} "
              f"[{r['d_ap_ci'][0]:+.4f}, {r['d_ap_ci'][1]:+.4f}]   AUC {r['linear']['auc']:.4f} -> "
              f"{r['smooth']['auc']:.4f}  dAUC {r['d_auc']:+.4f}   align peak ({r['alignment']['peak_dy']},"
              f"{r['alignment']['peak_dx']})")  # fmt: skip
    ok = [r for r in rows if "excluded" not in r]
    d_ap = [r["d_ap"] for r in ok]
    summary = {
        "n_included": len(ok),
        "n_excluded": len(rows) - len(ok),
        "d_ap_median": float(np.median(d_ap)) if d_ap else None,
        "d_ap_pos": sum(v > 0 for v in d_ap),
        "d_ap_neg": sum(v < 0 for v in d_ap),
        "resolved_pos": sum(r["d_ap_ci"][0] > 0 for r in ok),
        "resolved_neg": sum(r["d_ap_ci"][1] < 0 for r in ok),
        "abs_d_ap_below_0_02": sum(abs(v) < 0.02 for v in d_ap),
    }
    predictions = {
        "p1_abs_dAP_lt_0.02_in_6_of_8": summary["abs_d_ap_below_0_02"] >= 6,
        "p2_dAP_pos_in_at_most_5_of_8": summary["d_ap_pos"] <= 5,
    }
    if summary["resolved_pos"] >= 6:
        verdict = "smooth agrees better with villa's labels"
    elif summary["resolved_neg"] >= 6:
        verdict = "linear agrees better with villa's labels"
    else:
        verdict = "no consistent difference"
    res = {
        "segments": rows,
        "summary": summary,
        "predictions_held": predictions,
        "verdict": verdict,
    }
    out.write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print("predictions held:", predictions)
    print("VERDICT:", verdict)
    return 0


def selftest() -> int:
    from sklearn.metrics import average_precision_score, roc_auc_score

    rng = np.random.default_rng(0)
    for _ in range(5):
        y = rng.random(50_000) < 0.07
        s = np.clip(rng.normal(60 + 40 * y, 30), 0, 255).astype(np.uint8)
        m = metrics_from_hist(
            np.bincount(s[y], minlength=256), np.bincount(s[~y], minlength=256)
        )
        ap, auc = average_precision_score(y, s), roc_auc_score(y, s)
        assert abs(m["ap"] - ap) < 1e-9 and abs(m["auc"] - auc) < 1e-9, (m, ap, auc)
    print("selftest: histogram AP and AUC equal scikit-learn to 1e-9")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("maxcomp")
    m.add_argument("out", type=Path)
    m.add_argument("tifdir", type=Path)
    lb = sub.add_parser("labels")
    lb.add_argument("seg")
    lb.add_argument("out", type=Path)
    a = sub.add_parser("analyse")
    a.add_argument("--out", type=Path, default=Path("reports/interp_vs_labels.json"))
    sub.add_parser("selftest")
    args = ap.parse_args()
    if args.cmd == "maxcomp":
        maxcomp(args.out, args.tifdir)
        return 0
    if args.cmd == "labels":
        fetch_labels(args.seg, args.out)
        return 0
    if args.cmd == "selftest":
        return selftest()
    return analyse(args.out)


if __name__ == "__main__":
    sys.exit(main())
