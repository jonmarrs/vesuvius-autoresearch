"""Model baselines for the ScrollGT column-level target (pherc1667_merged_columns).

Runs arm C (3-scroll distilled student; trained on NO PHerc-1667 data) and the legacy
detector over a rendered multi-column region of the merged full-reading geometry, then
scores both through `scrollgt score-columns` with the region's grid origin. The
prediction maps are saved next to the scorecards so the numbers can be reviewed
visually — a column score without the map is not a submission (see BASELINES).

Region: cols 17-19 (text, single-strip, unflagged) — grid y0=100 x0=20800 h=1710 w=3990,
rendered by render_cli --tifxyz (fragment merged_cols17to19).
"""

import glob
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.scroll3_render import infer_no_label

FRAG_ROOT = "local_data/rendered_1667"
FRAG_ID = "merged_cols17to19"
ORIGIN = (100, 20800)
SCROLLGT = os.path.abspath("../scrollgt")
TARGET = os.path.join(SCROLLGT, "data/pherc1667_merged_columns")
ARM_C = "models/detector_xscroll_c/detector_epoch=11.ckpt"
LEGACY = "models/detector/detector_epoch=7.ckpt"
OUT = "reports/detector"


def main():
    frag = os.path.join(FRAG_ROOT, FRAG_ID)
    if not glob.glob(os.path.join(frag, "layers", "*.tif")):
        raise SystemExit(f"rendered fragment missing: {frag} — run the render first")
    rows = {}
    for name, ckpt in (("arm_C", ARM_C), ("legacy", LEGACY)):
        if not os.path.exists(ckpt):
            print(f"{name}: checkpoint {ckpt} missing — skipped", flush=True)
            continue
        import repro.sota_data.scroll3_render as s3r

        s3r.ARM_C = ckpt  # infer_no_label reads the module constant
        prob = infer_no_label(FRAG_ROOT, FRAG_ID).astype(np.float32)
        pred_path = os.path.join(OUT, f"columns_baseline_{name}_pred.npy")
        np.save(pred_path, prob)
        cv2.imwrite(
            os.path.join(OUT, f"columns_baseline_{name}_pred.png"),
            (np.clip(prob, 0, 1) * 255).astype(np.uint8)[::3, ::3],
        )
        card_path = os.path.join(OUT, f"columns_baseline_{name}.json")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "scrollgt.cli",
                "score-columns",
                pred_path,
                TARGET,
                "--origin",
                str(ORIGIN[0]),
                str(ORIGIN[1]),
                "--json-out",
                card_path,
            ],
            check=True,
            env={**os.environ, "PYTHONPATH": os.path.join(SCROLLGT, "src")},
        )
        rows[name] = json.load(open(card_path))["metrics"]
        os.remove(pred_path)  # keep the small png; the npy is 27MB
    print(json.dumps(rows, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
