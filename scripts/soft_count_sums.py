"""docs/preregistration/2026-10-04_soft_count.md -- per-arm soft and hard counts from a re-scored strip.

Reads <scored>/metrics.json (H, villa's own count, computed in float32 before saving) and the float16 probability map
<scored>/predictions/*_flat_prob.npy (S = sum, accumulated in float64). Writes one JSON.

Usage: soft_count_sums.py <scored_dir> <out_json>
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np

ROWS = 256


def sums(prob: np.ndarray) -> dict:
    soft = sub = 0.0
    hard16 = n = 0
    for i in range(0, prob.shape[0], ROWS):
        b = np.asarray(prob[i : i + ROWS], dtype=np.float64)
        hi = b >= 0.5
        soft += float(b.sum())
        sub += float(b[~hi].sum())
        hard16 += int(hi.sum())
        n += b.size
    return {"S": soft, "S_sub_threshold": sub, "H_from_float16": hard16, "pixels": n}


def main(argv: list[str]) -> int:
    scored, out = Path(argv[1]), Path(argv[2])
    probs = sorted(glob.glob(str(scored / "predictions" / "*_flat_prob.npy")))
    if len(probs) != 1:
        raise SystemExit(f"{scored}: expected one probability map, found {len(probs)}")
    summary = json.loads((scored / "metrics.json").read_text())["summary"]
    res = {"scored": str(scored), "prob": probs[0], "H": int(summary["total_fg_pixels"]),
           **sums(np.load(probs[0], mmap_mode="r"))}  # fmt: skip
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: res[k] for k in ("H", "S", "pixels")}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
