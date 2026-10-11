"""Post-hoc, not registered (finding 83): voxel recall and precision of ScrollGT's reference mask (fiber_hz_vt, P >= 0.5)
against villa's semantic label, on the 11 in-sample fiber targets and the 10 held-out Dataset004 cubes.

Labels are villa's current ones: Dataset004 for the three revised targets and the held-out cubes; the local copies
ScrollGT was built from for the other eight targets (their NMLs and CT are byte-identical in Dataset004; their labels
were not compared).

Usage: .venv/bin/python scripts/fiber_mask_vs_label.py [--out reports/fiber_heldout_mask_vs_label.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

NEO = Path("/home/jon/openclaw-workspace/Neo-VM")
IN_DIR = NEO / "projects/vesuvius-autoresearch/local_data/fiber_skeletons"
REVISED_DIR = NEO / "spiral_out/fiber_d004/labels"
HELD_DIR = NEO / "spiral_out/fiber_heldout/data"


def overlap(mask: np.ndarray, label: np.ndarray) -> dict:
    inter = int((mask & label).sum())
    nm, nl = int(mask.sum()), int(label.sum())
    return {"label_density": float(label.mean()), "mask_density": float(mask.mean()),
            "recall": inter / nl, "precision": inter / nm, "dice": 2 * inter / (nl + nm)}  # fmt: skip


def main() -> int:
    import tifffile

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/fiber_heldout_mask_vs_label.json")
    )
    args = ap.parse_args()
    jobs = []
    for p in sorted(IN_DIR.glob("*_fiberprob.npy")):
        c = p.name.removesuffix("_fiberprob.npy")
        rev = REVISED_DIR / f"{c}.tif"
        lab, src = (
            (rev, "Dataset004")
            if rev.exists()
            else (IN_DIR / f"{c}_semantic.tif", "scrollgt_build_copy")
        )
        jobs.append((c, "in_sample", p, lab, src))
    for p in sorted(HELD_DIR.glob("*_fiberprob.npy")):
        c = p.name.removesuffix("_fiberprob.npy")
        jobs.append((c, "held_out", p, HELD_DIR / f"{c}_semantic.tif", "Dataset004"))
    out = {}
    for c, split, prob, lab, src in jobs:
        r = {"split": split, "label_source": src,
             **overlap(np.load(prob) >= 0.5, tifffile.imread(lab) > 0)}  # fmt: skip
        out[c] = r
        print(
            c,
            split,
            src,
            {k: round(v, 4) for k, v in r.items() if isinstance(v, float)},
            flush=True,
        )
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
