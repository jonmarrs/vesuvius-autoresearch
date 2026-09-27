"""Pixel-compare two vc_render_tifxyz TIFF outputs of the SAME flat surface.

Answers the registered question of `docs/preregistration/2026-09-25_sampler_from_source.md` on the
fresh-directory reproduction: does a source-built sampler write the same sampled values as the
published one? Per slice: shape, exact equality, fraction of differing pixels, max |diff|, and
correlation over covered pixels. A slice that is missing or unreadable in either run is reported as
such and makes the verdict NOT COMPARABLE -- never silently skipped.

    compare_sampler_tifs.py <ref_tif_dir> <test_tif_dir> [--json out.json]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile


def compare_slice(a: np.ndarray, b: np.ndarray) -> dict:
    if a.shape != b.shape:
        return {"comparable": False, "reason": f"shape {a.shape} vs {b.shape}"}
    diff = a.astype(np.int16) - b.astype(np.int16)
    covered = (a > 0) | (b > 0)
    r = (
        float(np.corrcoef(a[covered].astype(float), b[covered].astype(float))[0, 1])
        if covered.sum() > 1 and a[covered].std() > 0 and b[covered].std() > 0
        else float("nan")
    )
    return {
        "comparable": True,
        "identical": bool(not diff.any()),
        "frac_px_differ": float((diff != 0).mean()),
        "max_abs_diff": int(np.abs(diff).max()),
        "mean_abs_diff_covered": float(np.abs(diff[covered]).mean())
        if covered.any()
        else 0.0,
        "r_covered": r,
    }


def verdict(slices: dict[str, dict]) -> str:
    if not slices or not all(s.get("comparable") for s in slices.values()):
        return "NOT COMPARABLE"
    if all(s["identical"] for s in slices.values()):
        return "BYTE-IDENTICAL SAMPLING"
    return "SAMPLED VALUES DIFFER"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ref", type=Path)
    ap.add_argument("test", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    names = sorted(
        {p.name for p in a.ref.glob("*.tif")} | {p.name for p in a.test.glob("*.tif")}
    )
    slices: dict[str, dict] = {}
    for n in names:
        try:
            slices[n] = compare_slice(
                tifffile.imread(a.ref / n), tifffile.imread(a.test / n)
            )
        except Exception as e:  # missing or torn slice: report, never skip
            slices[n] = {"comparable": False, "reason": f"{type(e).__name__}: {e}"}
    res = {
        "ref": str(a.ref),
        "test": str(a.test),
        "verdict": verdict(slices),
        "slices": slices,
    }
    if a.json:
        a.json.write_text(json.dumps(res, indent=2) + "\n")
    print(res["verdict"])
    for n, s in slices.items():
        print(" ", n, {k: v for k, v in s.items() if k != "comparable"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
