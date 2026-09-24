"""How much did the rendered strip's PIXELS change, per arm, against the 0 vx reference?

Descriptive, exploratory, not registered. It records what showed the scorer's block-level
rescoring does NOT track the size of the pixel change: the half-cell arm changed its
pixels less than the half-pixel arm on every measure, yet re-drew more
(`reports/re_sampling_is_enough.md`, "Not explained").

    python scripts/describe_rendered_pixel_change.py [--json out]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_resampling_or_distortion import parse_trim  # noqa: E402
from build_shifted_strip_arm import load_strip  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
ZERO = "flat_study_zero"
ARMS = {"rs_t005": 0.05, "rs_t05": 0.5}  # arm -> t (cell)


def change(z: np.ndarray, a: np.ndarray) -> dict[str, float]:
    m = (z > 8) | (a > 8)
    d = a.astype(np.int16) - z.astype(np.int16)
    s, ad = d[m], np.abs(d[m])
    return {
        "signed_mean": float(s.mean()),
        "mean_abs": float(ad.mean()),
        "p90_abs": float(np.percentile(ad, 90)),
        "frac_abs_ge_20": float((ad >= 20).mean()),
        "frac_abs_ge_50": float((ad >= 50).mean()),
        "frac_abs_ge_100": float((ad >= 100).mean()),
        "r": float(np.corrcoef(z[m].astype(float), a[m].astype(float))[0, 1]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    z = load_strip(SO / ZERO / "meshes" / "ink")
    out = {}
    for arm, t in ARMS.items():
        c, r = parse_trim(SO / f"{arm}.render.log")
        off = c * 10 + round(t * 10)
        s = load_strip(SO / arm / "meshes" / "ink")
        zz = z[r * 10 : r * 10 + s.shape[0], off : off + s.shape[1]]
        out[arm] = change(zz, s[:, : zz.shape[1]]) | {"offset_px": off}
        print(arm, {k: round(v, 4) for k, v in out[arm].items()})
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
