"""DESCRIPTIVE (not registered): how much of villa's annotated ink does villa's scorer mark, at villa's metric
settings? Finding 72's default-mode outputs; mesh-valid surface split into villa's supervised (annotated) region and
the rest. "Outside" is UNANNOTATED, not ink-free, so the inside/outside ratio is weak evidence either way.

Usage: .venv/bin/python scripts/scorer_sparsity_annotated.py [--out reports/scorer_sparsity_annotated.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scorer_tracking_gap import SEGS, G, lab_sup  # noqa: E402

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkagree/src")
from inkagree.compare import domain_mask  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/scorer_sparsity_annotated.json")
    )
    args = ap.parse_args()
    keys = ("in_px", "in_fg", "in_ink", "in_fg_on_ink", "out_px", "out_fg")
    per, tot = {}, dict.fromkeys(keys, 0)
    for seg in SEGS:
        d = G / "scorer_study" / seg
        m = np.asarray(Image.open(d / "linear/ink_metric/predictions/seg_mask.png")) > 0
        lab, sup = lab_sup(seg)
        H, W = min(m.shape[0], lab.shape[0]), min(m.shape[1], lab.shape[1])
        v = domain_mask(d / "mesh/x.tif", m.shape)[:H, :W]
        m, lab, sup = m[:H, :W], lab[:H, :W], sup[:H, :W]
        i, o = v & sup, v & ~sup
        c = {"in_px": int(i.sum()), "in_fg": int(m[i].sum()), "in_ink": int(lab[i].sum()),
             "in_fg_on_ink": int((m & lab & i).sum()), "out_px": int(o.sum()), "out_fg": int(m[o].sum())}  # fmt: skip
        per[seg] = c
        for k in keys:
            tot[k] += c[k]

    def rates(c: dict) -> dict:
        fi, fo = c["in_fg"] / c["in_px"], c["out_fg"] / c["out_px"]
        return {"fg_inside": fi, "fg_outside": fo, "inside_over_outside": fi / fo,
                "label_ink_inside": c["in_ink"] / c["in_px"],
                "precision_inside": c["in_fg_on_ink"] / max(c["in_fg"], 1),
                "recall_inside": c["in_fg_on_ink"] / c["in_ink"]}  # fmt: skip

    res = {"registered": False, "per_segment": {s: {**c, **rates(c)} for s, c in per.items()},
           "pooled": {**tot, **rates(tot)}}  # fmt: skip
    for s, r in [*res["per_segment"].items(), ("POOLED", res["pooled"])]:
        print(f"{s:15s} fg in {r['fg_inside']:.4f} out {r['fg_outside']:.4f} ratio {r['inside_over_outside']:.2f} | "
              f"label ink {r['label_ink_inside']:.3f} | precision {r['precision_inside']:.3f} recall {r['recall_inside']:.4f}")  # fmt: skip
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
