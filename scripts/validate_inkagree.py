"""Validate inkagree against findings 71 and 72: it must reproduce their registered numbers from the same inputs.

Known answers, read from the committed artifacts (never typed in):

* finding 71, `reports/interp_vs_labels.json`: rendered 3D-ink prediction, linear vs smooth, labels level 2,
  8 segments. Original analysis: central 4096-px gate window, shift 3; 512-px blocks; one generator
  (seed 20261003) shared across segments in order, consumed by included segments only.
* finding 72, `reports/scorer_vs_labels.json`: villa's scorer probability, linear vs smooth, labels level 3.
  Original analysis: whole-domain gate on the linear STRIP; 256-px blocks; one shared generator, consumed per
  segment by the probability bootstrap and then the strip bootstrap.

inkagree is driven through its library API with the same parameters and the same generator sequence. Point
estimates (AP, AUC, dAP) must match to 1e-12; the bootstrap intervals must match exactly. One intended
difference is checked rather than hidden: in finding 71, segment 20230929220926 was excluded as "misaligned"
because of the NaN defect; inkagree's fixed gate must call it "undetermined".

Usage: .venv/bin/python scripts/validate_inkagree.py [--out reports/inkagree_validation.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkagree/src")
from inkagree.compare import compare_arms, domain_mask, load_arm  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp")
SEED = 20261003
TOL = 1e-12


def check_f71(results: list) -> None:
    reg = {
        r["segment"]: r
        for r in json.loads(Path("reports/interp_vs_labels.json").read_text())[
            "segments"
        ]
    }
    rng = np.random.default_rng(SEED)
    for seg, r in reg.items():
        d = SO / "study" / seg
        a, b = load_arm(d / "linear_max.tif"), load_arm(d / "smooth_max.tif")
        ink = np.load(d / "labels_L2.npy") > 127
        dom = domain_mask(d / "mesh" / "x.tif", a.shape)
        res = compare_arms(a, b, ink, dom, block=512, n_boot=2000, gate_shift=3, gate_window=4096,
                           gate_min_gain=0.0, rng=rng)  # fmt: skip
        row = {"finding": 71, "segment": seg}
        if "excluded" in r:
            want = "undetermined" if seg == "20230929220926" else "misaligned"
            row.update(
                registered=r["excluded"],
                inkagree=res["status"],
                expected=want,
                ok=res["status"] == want,
            )
        else:
            ok = (
                res["passes"]
                and abs(res["a"]["ap"] - r["linear"]["ap"]) < TOL
                and abs(res["b"]["ap"] - r["smooth"]["ap"]) < TOL
                and abs(res["d_ap"] - r["d_ap"]) < TOL
                and abs(res["d_auc"] - r["d_auc"]) < TOL
                and res["d_ap_ci"] == r["d_ap_ci"]
                and res["d_auc_ci"] == r["d_auc_ci"]
            )
            row.update(status=res["status"], d_ap=res.get("d_ap"), d_ap_registered=r["d_ap"],
                       ci=res.get("d_ap_ci"), ci_registered=r["d_ap_ci"], ok=ok)  # fmt: skip
        results.append(row)


def check_f72(results: list) -> None:
    reg = {
        r["segment"]: r
        for r in json.loads(Path("reports/scorer_vs_labels.json").read_text())[
            "segments"
        ]
    }
    rng = np.random.default_rng(SEED)
    for seg, r in reg.items():
        d = SO / "scorer_study" / seg
        ink = np.load(d / "labels_L3.npy") > 127
        pa = load_arm(d / "linear/ink_metric/predictions/seg_flat_prob.npy")
        pb = load_arm(d / "smooth/ink_metric/predictions/seg_flat_prob.npy")
        sa = load_arm_jpg(d / "linear/meshes/ink/seg.jpg")
        sb = load_arm_jpg(d / "smooth/meshes/ink/seg.jpg")
        dom = domain_mask(d / "mesh" / "x.tif", pa.shape)
        # f72 gated on the linear STRIP (the scorer's probability map is too weak/smooth to gate on)
        rp = compare_arms(
            pa,
            pb,
            ink,
            dom,
            block=256,
            n_boot=2000,
            gate_min_gain=0.0,
            gate_image=sa,
            rng=rng,
        )
        rs = compare_arms(
            sa, sb, ink, dom, block=256, n_boot=2000, gate_min_gain=0.0, rng=rng
        )  # same rng order
        ok = (
            rp["passes"]
            and rs["passes"]
            and abs(rp["a"]["ap"] - r["prob"]["linear"]["ap"]) < TOL
            and abs(rp["d_ap"] - r["prob"]["d_ap"]) < TOL
            and rp["d_ap_ci"] == r["prob"]["d_ap_ci"]
            and abs(rs["d_ap"] - r["strip"]["d_ap"]) < TOL
            and rs["d_ap_ci"] == r["strip"]["d_ap_ci"]
        )
        results.append({"finding": 72, "segment": seg, "status": (rp["status"], rs["status"]),
                        "prob_d_ap": rp.get("d_ap"), "prob_d_ap_registered": r["prob"]["d_ap"],
                        "prob_ci": rp.get("d_ap_ci"), "prob_ci_registered": r["prob"]["d_ap_ci"], "ok": ok})  # fmt: skip


def load_arm_jpg(path: Path) -> np.ndarray:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    return np.asarray(Image.open(path))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/inkagree_validation.json")
    )
    args = ap.parse_args()
    results: list = []
    check_f71(results)
    check_f72(results)
    n_ok = sum(r["ok"] for r in results)
    for r in results:
        print(("PASS" if r["ok"] else "FAIL"), r["finding"], r["segment"],
              {k: v for k, v in r.items() if k not in ("finding", "segment", "ok")})  # fmt: skip
    print(f"\n{n_ok}/{len(results)} reproduce the registered result")
    args.out.write_text(
        json.dumps(
            {"tolerance": TOL, "results": results, "n_ok": n_ok, "n": len(results)},
            indent=2,
        )
        + "\n"
    )
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
