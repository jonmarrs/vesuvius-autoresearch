"""Compare the #1818 smoke crops (repro/spiral_render/smoke_surface_interpolation.sh).

Per slice: A vs B (is the post-#1818 default byte-identical to the pre-#1818 build?), B vs C
(what does --surface-interpolation smooth change?), and B vs the same window cut from the PR #1905
build's full render of this flat (are the crop coordinates the full-render pixel grid?).

Usage: .venv/bin/python scripts/compare_interp_smoke.py [--out reports/interp_smoke.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
SMOKE = SO / "interp_smoke"
FULL_PR1905 = SO / "tif_score_pr1905/meshes/concat/w120-129_flat/ink"
X0, Y0, W, H = 59392, 1536, 2048, 1024


def slices(d: Path) -> list[np.ndarray]:
    return [tifffile.imread(f) for f in sorted(d.glob("*.tif"))]


def diff(a: np.ndarray, b: np.ndarray) -> dict:
    if a.shape != b.shape:
        return {"shape_a": list(a.shape), "shape_b": list(b.shape), "identical": False}
    d = a.astype(np.int32) - b.astype(np.int32)
    nz = d != 0
    return {
        "identical": bool(not nz.any()),
        "n_px": int(d.size),
        "n_differ": int(nz.sum()),
        "frac_differ": float(nz.mean()),
        "max_abs": int(np.abs(d).max()),
        "mean_abs": float(np.abs(d).mean()),
        "mean_a": float(a.mean()),
        "mean_b": float(b.mean()),
        "frac_ge64_a": float((a >= 64).mean()),
        "frac_ge64_b": float((b >= 64).mean()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/interp_smoke.json")
    args = ap.parse_args()
    A, B, C = (slices(SMOKE / n) for n in "ABC")
    full = [s[Y0 : Y0 + H, X0 : X0 + W] for s in slices(FULL_PR1905)]
    out = {
        "crop": {"x": X0, "y": Y0, "w": W, "h": H},
        "samplers": {
            n: (SMOKE / f"{n}.SAMPLER_SHA").read_text().strip() for n in "ABC"
        },
        "n_slices": {n: len(v) for n, v in zip("ABC", (A, B, C), strict=False)},
        "A_vs_B": [diff(a, b) for a, b in zip(A, B, strict=False)],
        "B_vs_C": [diff(b, c) for b, c in zip(B, C, strict=False)],
        "B_vs_pr1905_full_window": [diff(b, f) for b, f in zip(B, full, strict=False)],
    }
    # the strip render_ink scores is the max-composite over the slices
    if A and B and C:
        mc = {
            n: np.max(np.stack(v), axis=0)
            for n, v in zip("ABC", (A, B, C), strict=False)
        }
        out["maxcomposite_B_vs_C"] = diff(mc["B"], mc["C"])
        out["maxcomposite_A_vs_B"] = diff(mc["A"], mc["B"])
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    for k in ("A_vs_B", "B_vs_C", "B_vs_pr1905_full_window"):
        print(
            k,
            [(r.get("identical"), r.get("n_differ"), r.get("max_abs")) for r in out[k]],
        )
    for k in ("maxcomposite_A_vs_B", "maxcomposite_B_vs_C"):
        if k in out:
            r = out[k]
            print(k, {x: r.get(x) for x in ("identical", "frac_differ", "max_abs", "mean_a", "mean_b",
                                            "frac_ge64_a", "frac_ge64_b")})  # fmt: skip


if __name__ == "__main__":
    main()
