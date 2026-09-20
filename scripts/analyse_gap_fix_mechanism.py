"""Where does the gap-expander fix's 10% ink loss come from?

`reports/gap_fix_costs_ink_established.md` established that raising
`model_gap_expander_num_windings` 130 -> 133 -- a config CORRECTNESS fix, clearing
a warning that the capacity was short of `shell_outer_winding_idx` -- costs
**10.35%** of `total_fg_pixels` over w120-w129, on twelve fits.

The obvious benign explanation is that the fix removes DUPLICATED coverage.
`reports/duplicate_coverage_inflates_the_objective.md` showed an arm gaining
12.59% ink from a mesh that adds **zero new papyrus**, so the objective is known
to reward duplication. If the fix removes some, the "cost" would be deflation of
an inflated number rather than lost text -- which would reverse the finding's
meaning entirely.

This tests that, and it fails. Reported because the alternative it leaves is
sharper than the hypothesis it kills.

Run after `measure_winding_overlap.py --dump-windings` for each arm.
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
from scipy import stats

BASE = ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06")
GAP = ("gap133", "gap133s2", "gap133s3", "gap133s4", "gap133s5", "gap133s6")
OUTER_FROM = 120  # the scored ROI is w120-w129


def compare(b: list[float], g: list[float]) -> tuple[float, float]:
    rel = (st.mean(g) - st.mean(b)) / st.mean(b)
    _, p = stats.ttest_ind(b, g, equal_var=False)
    return rel, float(p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument(
        "--overlap-dir",
        required=True,
        help="dir holding ovw_<arm>.json and w_<arm>.npy from measure_winding_overlap.py",
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    od = Path(a.overlap_dir)

    def ink(tag: str, key: str) -> float:
        p = Path(a.spiral_out) / f"outer_{tag}" / "ink_metric" / "metrics.json"
        return json.loads(p.read_text())["summary"][key]

    def occupied(tag: str) -> float:
        return json.loads((od / f"ovw_{tag}.json").read_text())["quant"]["4"][
            "occupied"
        ]

    def dup_all(tag: str) -> float:
        return json.loads((od / f"ovw_{tag}.json").read_text())["quant"]["4"][
            "far_gap2"
        ]

    def dup_outer(tag: str) -> float:
        w = np.load(od / f"w_{tag}.npy")
        return float(((w[:, 1] >= OUTER_FROM) | (w[:, 2] >= OUTER_FROM)).sum())

    rows = {
        "ink  total_fg_pixels": lambda t: ink(t, "total_fg_pixels"),
        "ink density  fg_fraction": lambda t: ink(t, "overall_fg_fraction"),
        "2D strip area": lambda t: ink(t, "total_pixels"),
        "3D occupied cells": occupied,
        "duplicated cells (all w)": dup_all,
        f"duplicated cells (w>={OUTER_FROM})": dup_outer,
    }

    print("GAP-EXPANDER FIX: what moved, baseline(6) vs gap133(6)\n")
    print(f"{'quantity':<34}{'baseline':>16}{'gap133':>16}{'rel':>9}{'p':>9}")
    out = {}
    for label, fn in rows.items():
        b = [fn(t) for t in BASE]
        g = [fn(t) for t in GAP]
        rel, p = compare(b, g)
        out[label] = {"baseline": st.mean(b), "gap133": st.mean(g), "rel": rel, "p": p}
        print(
            f"{label:<34}{st.mean(b):>16,.4g}{st.mean(g):>16,.4g}{rel:>+8.2%}{p:>9.4f}"
        )

    print("\nThe canvas did not shrink and the duplication did not fall. A same-sized")
    print("surface yields 10% less ink, so the fix RELOCATES or RE-SAMPLES it rather")
    print("than removing double-counted coverage.")

    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
