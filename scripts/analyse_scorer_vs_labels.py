"""docs/preregistration/2026-10-03_scorer_sensitivity_vs_labels.md -- villa's 2D scorer on the 8 labelled
Scroll-1 segments, linear vs smooth renders at the metric's own settings.

    strip ARM TIFDIR     ARM/meshes/ink/seg.jpg from TIFDIR (render_ink's strip, verbatim) + the keep-prob scorer tree
    labels SEG OUT       fetch SEG's level-3 label raster (20260918) -> OUT (.npy)
    analyse [--out]      outcome A (count sensitivity), outcome B (faithfulness), alignment gate (fixed)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_interp_vs_labels import (  # noqa: E402  (verified metrics: selftest == sklearn to 1e-9)
    BUCKET,
    SEED,
    SEGMENTS,
    block_hists,
    domain_mask,
    metrics_from_hist,
)

Image.MAX_IMAGE_PIXELS = None
WORK = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp/scorer_study")
SCORER_TREE = Path(
    "/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp/scorer_tree/spiral-fitting"
)
LABEL_L3 = "PHercParis4/segments/{seg}/ink-labels/2.4um-volume-20260411134726/20260918/inklabels.zarr/3/"
WIN, MIN_COUNT, SHIFT, GATE_TOL, N_BOOT = 2048, 1000, 2, 1, 2000
BLOCK3 = 256


def build_strip(arm: Path, tifdir: Path) -> None:
    tifs = sorted(tifdir.glob("*.tif"))
    if len(tifs) != 5:
        sys.exit(f"{tifdir}: {len(tifs)} slices, expected 5")
    comp = None
    for f in tifs:  # render_ink.max_composite, verbatim
        layer = np.asarray(Image.open(f))
        comp = layer if comp is None else np.maximum(comp, layer)
    assert comp is not None
    strip = comp.astype(np.float32)
    p95 = np.percentile(strip, 95)
    strip = np.clip(strip / p95, 0, 1) * 255 if p95 > 0 else strip
    (arm / "meshes/ink").mkdir(parents=True)
    shutil.copytree(SCORER_TREE, arm / "spiral-fitting", symlinks=True)
    Image.fromarray(strip.astype(np.uint8)).save(arm / "meshes/ink/seg.jpg", quality=95)
    print(f"strip {arm}: {strip.shape} p95={p95}")


def fetch_labels(seg: str, out: Path) -> None:
    import tensorstore as ts

    t = ts.open({"driver": "zarr3", "kvstore": {"driver": "http", "base_url": BUCKET,
                                                "path": LABEL_L3.format(seg=seg)}}).result()  # fmt: skip
    a = t.read().result()
    assert a.dtype == np.uint8, a.dtype
    np.save(out, a)
    print(f"labels L3 {seg}: {a.shape}, ink {float((a > 127).mean()):.4f}")


def load_arm(arm: Path) -> dict:
    pred = arm / "ink_metric" / "predictions"
    mask = np.asarray(Image.open(pred / "seg_mask.png")) > 0
    prob = np.load(pred / "seg_flat_prob.npy").astype(np.float32)
    strip = np.asarray(Image.open(arm / "meshes/ink/seg.jpg"))
    total = json.loads((arm / "ink_metric/metrics.json").read_text())["summary"][
        "total_fg_pixels"
    ]
    assert int(mask.sum()) == total, (
        f"{arm}: mask sum {int(mask.sum())} != total_fg_pixels {total}"
    )
    q = np.clip(np.rint(prob * 255), 0, 255).astype(np.uint8)
    return {"mask": mask, "prob_q": q, "strip": strip, "total": total}


def gate(score: np.ndarray, lab: np.ndarray, dom: np.ndarray) -> dict:
    """Strip-intensity AUC at label offsets (dy, dx) in [-SHIFT, SHIFT]^2 over the whole domain.
    score[y, x] is compared with label[y + dy, x + dx]. Undefined (NaN) AUCs never win."""
    H, W = score.shape
    k = SHIFT
    s, d = score[k : H - k, k : W - k], dom[k : H - k, k : W - k]
    res = {}
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            ll = lab[k + dy : H - k + dy, k + dx : W - k + dx] > 127
            p = np.bincount(s[d & ll].ravel(), minlength=256)
            n = np.bincount(s[d & ~ll].ravel(), minlength=256)
            res[(dy, dx)] = metrics_from_hist(p, n)["auc"]
    finite = {kk: v for kk, v in res.items() if np.isfinite(v)}
    if not finite:
        return {"status": "undetermined", "passes": False}
    (py, px), best = max(finite.items(), key=lambda kv: kv[1])
    ok = abs(py) <= GATE_TOL and abs(px) <= GATE_TOL
    return {"status": "aligned" if ok else "misaligned", "passes": ok, "peak_dy": py, "peak_dx": px,
            "peak_auc": best, "auc_at_0": res[(0, 0)]}  # fmt: skip


def boot_delta(hl: tuple, hs: tuple, rng: np.random.Generator) -> dict:
    (pl, nl), (ps, ns) = hl, hs
    occ = np.flatnonzero((pl + nl).sum(1) > 0)
    nb = pl.shape[0]
    d_ap, d_auc = [], []
    for _ in range(N_BOOT):
        w = np.bincount(rng.choice(occ, size=len(occ), replace=True), minlength=nb)
        a, b = metrics_from_hist(w @ pl, w @ nl), metrics_from_hist(w @ ps, w @ ns)
        d_ap.append(b["ap"] - a["ap"])
        d_auc.append(b["auc"] - a["auc"])
    q = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]  # noqa: E731
    return {"d_ap_ci": q(d_ap), "d_auc_ci": q(d_auc), "n_blocks": int(len(occ))}


def analyse_segment(seg: str, rng: np.random.Generator) -> dict:
    import analyse_interp_vs_labels as base

    d = WORK / seg
    lab = np.load(d / "labels_L3.npy")
    lin, smo = load_arm(d / "linear"), load_arm(d / "smooth")
    full_dom = domain_mask(
        d / "mesh" / "x.tif", lin["mask"].shape
    )  # mapping on the full canvas, then crop
    H = min(lab.shape[0], lin["mask"].shape[0], smo["mask"].shape[0])
    W = min(lab.shape[1], lin["mask"].shape[1], smo["mask"].shape[1])
    crop = lambda a: a[:H, :W]  # noqa: E731
    lab = crop(lab)
    for arm in (lin, smo):
        for key in ("mask", "prob_q", "strip"):
            arm[key] = crop(arm[key])
    dom = full_dom[:H, :W]
    assert dom.shape == lab.shape == lin["mask"].shape
    row: dict = {
        "segment": seg,
        "shape": [H, W],
        "label_shape": list(np.load(d / "labels_L3.npy").shape),
    }
    # outcome A: count sensitivity per full-height column window (counts on the whole canvas, as the scorer)
    wins = []
    for x0 in range(0, W - WIN + 1, WIN):
        cl, cs = (
            int(lin["mask"][:, x0 : x0 + WIN].sum()),
            int(smo["mask"][:, x0 : x0 + WIN].sum()),
        )
        if cl >= MIN_COUNT:
            wins.append({"x0": x0, "linear": cl, "smooth": cs, "d": cs / cl - 1})
    row["windows"] = wins
    row["total_linear"], row["total_smooth"] = lin["total"], smo["total"]
    row["d_total"] = smo["total"] / lin["total"] - 1 if lin["total"] else None
    # gate on the linear strip intensity
    g = gate(lin["strip"], lab, dom)
    row["gate"] = g
    if not g["passes"]:
        row["excluded"] = g["status"]
        return row
    # outcome B: faithfulness of the scorer probability, and of the raw strip
    base.BLOCK = BLOCK3
    for name, key in (("prob", "prob_q"), ("strip", "strip")):
        hl, hs = block_hists(lin[key], lab, dom), block_hists(smo[key], lab, dom)
        ml, ms = (
            metrics_from_hist(hl[0].sum(0), hl[1].sum(0)),
            metrics_from_hist(hs[0].sum(0), hs[1].sum(0)),
        )
        row[name] = {"linear": ml, "smooth": ms, "d_ap": ms["ap"] - ml["ap"], "d_auc": ms["auc"] - ml["auc"],
                     **boot_delta(hl, hs, rng)}  # fmt: skip
    return row


def analyse(out: Path) -> int:
    rng = np.random.default_rng(SEED)
    rows = [analyse_segment(s, rng) for s in SEGMENTS]
    wins = [w for r in rows for w in r["windows"]]
    big = [w for w in wins if abs(w["d"]) >= 0.05]
    inc = [r for r in rows if "excluded" not in r]
    dap = [r["prob"]["d_ap"] for r in inc]
    summary = {
        "n_windows": len(wins),
        "n_windows_abs_d_ge_5pct": len(big),
        "frac_windows_abs_d_ge_5pct": len(big) / len(wins) if wins else None,
        "window_d_range": [min(w["d"] for w in wins), max(w["d"] for w in wins)]
        if wins
        else None,
        "n_included": len(inc),
        "excluded": {r["segment"]: r["excluded"] for r in rows if "excluded" in r},
        "prob_d_ap": {r["segment"]: r["prob"]["d_ap"] for r in inc},
        "prob_abs_d_ap_lt_0_01": sum(abs(v) < 0.01 for v in dap),
        "prob_resolved_pos": sum(r["prob"]["d_ap_ci"][0] > 0 for r in inc),
        "prob_resolved_neg": sum(r["prob"]["d_ap_ci"][1] < 0 for r in inc),
    }
    predictions = {
        "p1_count_sensitive_ge_25pct_windows": (
            summary["frac_windows_abs_d_ge_5pct"] or 0
        )
        >= 0.25,
        "p2_faithfulness_abs_dAP_lt_0.01_in_6": summary["prob_abs_d_ap_lt_0_01"] >= 6,
    }
    out.write_text(json.dumps({"segments": rows, "summary": summary, "predictions_held": predictions},
                              indent=2, default=float) + "\n")  # fmt: skip
    for r in rows:
        tag = (
            f"EXCLUDED ({r['excluded']})"
            if "excluded" in r
            else (
                f"prob AP {r['prob']['linear']['ap']:.4f}->{r['prob']['smooth']['ap']:.4f} dAP {r['prob']['d_ap']:+.4f} "
                f"[{r['prob']['d_ap_ci'][0]:+.4f},{r['prob']['d_ap_ci'][1]:+.4f}]  strip dAP {r['strip']['d_ap']:+.5f}"
            )
        )
        ds = [round(w["d"] * 100, 1) for w in r["windows"]]
        print(f"{r['segment']}: total {r['d_total']:+.2%}  windows {ds}  {tag}")
    print(json.dumps(summary, indent=2, default=float))
    print("predictions held:", predictions)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("strip")
    s.add_argument("arm", type=Path)
    s.add_argument("tifdir", type=Path)
    lb = sub.add_parser("labels")
    lb.add_argument("seg")
    lb.add_argument("out", type=Path)
    a = sub.add_parser("analyse")
    a.add_argument("--out", type=Path, default=Path("reports/scorer_vs_labels.json"))
    args = ap.parse_args()
    if args.cmd == "strip":
        build_strip(args.arm, args.tifdir)
    elif args.cmd == "labels":
        fetch_labels(args.seg, args.out)
    else:
        return analyse(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
