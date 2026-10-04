"""docs/preregistration/2026-10-04_supervised_reanalysis.md -- findings 71-76 recomputed on villa's supervised region.

Same stored arms, labels, parameters and bootstrap as each finding; one change: domain = mesh-valid AND
supervised (villa's supervision.zarr at the label level). Gate: inkagree defaults (whole domain, +/-2 px,
min_gain 0.002) everywhere. Writes reports/supervised_reanalysis.json and prints each finding's verdict on
both domains.

Usage: .venv/bin/python scripts/reanalyse_supervised.py [--out reports/supervised_reanalysis.json]
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage, stats

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkagree/src")
from inkagree.compare import compare_arms, domain_mask, load_arm  # noqa: E402
from inkagree.labels import fetch_labels, fetch_supervision  # noqa: E402
from inkagree.metrics import metrics_from_hist  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
SEGS = (
    "20230702185753 20230929220926 20231007101619 20231012184424 "
    "20231016151002 20231031143852 20231106155351 20231210121321"
).split()
SEED, N_BOOT = 20261003, 2000


@functools.cache
def labels(seg: str, level: int) -> np.ndarray:
    return fetch_labels(seg, level)


@functools.cache
def supervision(seg: str, level: int) -> np.ndarray:
    s = fetch_supervision(seg, level)
    if s is None:
        raise RuntimeError(f"{seg}: no supervision mask at level {level}")
    return s


def jpg(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p))


def pair(
    seg: str,
    level: int,
    a: np.ndarray,
    b: np.ndarray,
    mesh_x: Path,
    block: int,
    gate_image=None,
) -> dict:
    dom = domain_mask(mesh_x, a.shape)
    rng = np.random.default_rng(SEED)
    r = compare_arms(a, b, labels(seg, level), dom, block=block, n_boot=N_BOOT, rng=rng, gate_image=gate_image,
                     supervision=supervision(seg, level))  # fmt: skip
    keep = (
        "status",
        "domain",
        "domain_px",
        "mesh_domain_px",
        "label_ink_frac",
        "d_ap",
        "d_ap_ci",
        "d_auc",
        "verdict",
    )
    out = {k: r.get(k) for k in keep}
    if r.get("passes"):
        out["ap_a"], out["ap_b"] = r["a"]["ap"], r["b"]["ap"]
    out["gate"] = {
        k: r["gate"].get(k) for k in ("status", "peak_dy", "peak_dx", "gain")
    }
    return out


def tally(rows: list[dict]) -> dict:
    c = [r for r in rows if r["status"] == "compared"]
    return {
        "n_compared": len(c),
        "resolved_b": sum(r["d_ap_ci"][0] > 0 for r in c),
        "resolved_a": sum(r["d_ap_ci"][1] < 0 for r in c),
        "b_ge_a": sum(r["d_ap"] >= 0 for r in c),
        "abs_lt_0_01": sum(abs(r["d_ap"]) < 0.01 for r in c),
        "median_d_ap": float(np.median([r["d_ap"] for r in c])) if c else None,
        "median_ap_a": float(np.median([r["ap_a"] for r in c])) if c else None,
        "not_compared": {
            r["segment"]: r["status"] for r in rows if r["status"] != "compared"
        },
    }


def f71() -> dict:
    rows = []
    for s in SEGS:
        d = SO / "gt_interp/study" / s
        r = pair(
            s,
            2,
            load_arm(d / "linear_max.tif"),
            load_arm(d / "smooth_max.tif"),
            d / "mesh/x.tif",
            512,
        )
        rows.append({"segment": s, **r})
    t = tally(rows)
    t["survives"] = (
        t["resolved_b"] < 6 and t["resolved_a"] < 6
    )  # registered: no consistent difference
    return {"rows": rows, "tally": t}


def f72_like(study: str) -> dict:
    prob_rows, strip_rows = [], []
    for s in SEGS:
        d = SO / "gt_interp" / study / s
        sa, sb = (
            jpg(d / "linear/meshes/ink/seg.jpg"),
            jpg(d / "smooth/meshes/ink/seg.jpg"),
        )
        pa = load_arm(d / "linear/ink_metric/predictions/seg_flat_prob.npy")
        pb = load_arm(d / "smooth/ink_metric/predictions/seg_flat_prob.npy")
        prob_rows.append(
            {"segment": s, **pair(s, 3, pa, pb, d / "mesh/x.tif", 256, gate_image=sa)}
        )
        strip_rows.append({"segment": s, **pair(s, 3, sa, sb, d / "mesh/x.tif", 256)})
    return {
        "prob": {"rows": prob_rows, "tally": tally(prob_rows)},
        "strip": {"rows": strip_rows, "tally": tally(strip_rows)},
    }


def steps(study: str, level: int, ref: str, others: tuple[str, ...]) -> dict:
    out = {}
    for x in others:
        rows = []
        for s in SEGS:
            d = SO / study / s
            r = pair(
                s,
                level,
                load_arm(d / f"step{ref}.tif"),
                load_arm(d / f"step{x}.tif"),
                d / "mesh/x.tif",
                256,
            )
            rows.append({"segment": s, **r})
        out[x] = {"rows": rows, "tally": tally(rows)}
    return out


def f76() -> dict:
    W, MIN_SUP = 2048, 0.25
    windows, hists = (
        [],
        {
            r: {
                "p": [np.zeros(256), np.zeros(256)],
                "s": [np.zeros(256), np.zeros(256)],
            }
            for r in (0, 1, 2, 4, 8)
        },
    )
    for seg in SEGS:
        d = SO / "gt_interp/scorer_study" / seg
        mask = (
            np.asarray(Image.open(d / "linear/ink_metric/predictions/seg_mask.png")) > 0
        )
        prob = load_arm(d / "linear/ink_metric/predictions/seg_flat_prob.npy")
        strip = jpg(d / "linear/meshes/ink/seg.jpg")
        lab, sup = labels(seg, 3), supervision(seg, 3)
        H = min(a.shape[0] for a in (mask, prob, strip, lab, sup))
        Wd = min(a.shape[1] for a in (mask, prob, strip, lab, sup))
        dom = domain_mask(d / "mesh/x.tif", mask.shape)[:H, :Wd] & sup[:H, :Wd]
        mask, prob, strip, lab = (
            mask[:H, :Wd],
            prob[:H, :Wd],
            strip[:H, :Wd],
            lab[:H, :Wd],
        )
        mdom = domain_mask(d / "mesh/x.tif", (H, Wd))
        for x0 in range(0, Wd - W + 1, W):
            sl = (slice(None), slice(x0, x0 + W))
            dd, md = dom[sl], mdom[sl]
            if md.sum() == 0 or dd.sum() < MIN_SUP * md.sum():
                continue
            windows.append({"segment": seg, "x0": x0, "sup_px": int(dd.sum()),
                            "scorer_density": float(mask[sl][dd].mean()), "label_density": float(lab[sl][dd].mean()),
                            "strip_density": float(strip[sl][dd].mean()) / 255})  # fmt: skip
        for r in hists:
            lr = ndimage.binary_dilation(lab, iterations=r) & sup[:H, :Wd] if r else lab
            for key, img in (("p", prob), ("s", strip)):
                hists[r][key][0] += np.bincount(img[dom & lr], minlength=256)
                hists[r][key][1] += np.bincount(img[dom & ~lr], minlength=256)
    q2 = []
    for r, h in hists.items():
        ap_p, ap_s = metrics_from_hist(*h["p"])["ap"], metrics_from_hist(*h["s"])["ap"]
        q2.append(
            {
                "dilation_px": r,
                "ap_scorer": ap_p,
                "ap_strip": ap_s,
                "ratio": ap_p / ap_s,
            }
        )
    q1 = {}
    for key in ("scorer_density", "strip_density"):
        if len(windows) >= 3:
            q1[key] = float(
                stats.spearmanr(
                    [w[key] for w in windows], [w["label_density"] for w in windows]
                ).statistic
            )
    ratios = [x["ratio"] for x in q2]
    return {"windows": windows, "n_windows": len(windows), "q1_rho": q1, "q2": q2,
            "q2_ratio_rises": all(b >= a for a, b in zip(ratios, ratios[1:], strict=False)) and ratios[-1] > ratios[0]}  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/supervised_reanalysis.json")
    )
    args = ap.parse_args()
    res = {
        "f71": f71(),
        "f72": f72_like("scorer_study"),
        "f73": f72_like("scorer_study_coarse"),
        "f74": steps("band_study", 2, "0.5", ("0.25", "1.0", "2.0")),
        "f75": steps("route_study", 3, "1.0", ("0.5", "2.0")),
        "f76": f76(),
    }
    res["f72"]["survives_p2"] = res["f72"]["prob"]["tally"]["abs_lt_0_01"] >= 6
    res["f73"]["survives_p2"] = res["f73"]["prob"]["tally"]["b_ge_a"] < 6
    res["f74"]["survives"] = all(
        v["tally"]["resolved_a"] >= 6
        for v in res["f74"].values()
        if isinstance(v, dict)
    )
    res["f75"]["survives"] = (
        res["f75"]["0.5"]["tally"]["resolved_a"] >= 6
        and res["f75"]["2.0"]["tally"]["resolved_b"] >= 6
    )
    args.out.write_text(json.dumps(res, indent=2, default=float) + "\n")
    t = lambda x: x["tally"]  # noqa: E731
    print(
        "f71 smooth vs linear (L2):",
        t(res["f71"]),
        "survives:",
        res["f71"]["tally"]["survives"],
    )
    for f in ("f72", "f73"):
        print(f"{f} scorer prob:", t(res[f]["prob"]))
        print(f"{f} strip:      ", t(res[f]["strip"]))
    print(
        "f72 survives P2:",
        res["f72"]["survives_p2"],
        "| f73 survives P2:",
        res["f73"]["survives_p2"],
    )
    for x in ("0.25", "1.0", "2.0"):
        print(f"f74 step {x} vs 0.5:", t(res["f74"][x]))
    print("f74 survives:", res["f74"]["survives"])
    for x in ("0.5", "2.0"):
        print(f"f75 step {x} vs 1.0:", t(res["f75"][x]))
    print("f75 survives:", res["f75"]["survives"])
    f = res["f76"]
    print(f"f76: {f['n_windows']} windows with >=25% supervised; Q1 rho {f['q1_rho']}; Q2 ratios",
          [round(float(x["ratio"]), 3) for x in f["q2"]], "rises:", f["q2_ratio_rises"])  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
