"""docs/preregistration/2026-10-03_shared_p95_normalisation.md -- finding 70's windows re-scored with ONE p95 per
mode (pooled over the 8 windows) instead of each window's own.

    build      arms under spiral_out/interp_shared_p95/w<x>/<mode>/ (strip + pinned scorer tree); prints them
    report     per-window delta vs finding 70's per-crop delta  [--out reports/shared_p95_rescore.json]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
F70 = SO / "interp_windows"
OUT = SO / "interp_shared_p95"
SF = SO / "detfit_up1/spiral-fitting"
MODES = ("linear", "smooth")


def windows() -> list[int]:
    return [int(x) for x in (F70 / "WINDOWS").read_text().split()]


def composite(tifdir: Path) -> np.ndarray:  # render_ink.max_composite, verbatim
    comp = None
    for f in sorted(tifdir.glob("*.tif")):
        layer = np.asarray(Image.open(f))
        comp = layer if comp is None else np.maximum(comp, layer)
    assert comp is not None
    return comp


def build() -> None:
    if OUT.exists():
        sys.exit(f"{OUT} exists")
    xs = windows()
    for mode in MODES:
        comps = {x: composite(F70 / f"w{x}" / mode / "tif") for x in xs}
        p95 = float(
            np.percentile(
                np.concatenate([c.ravel() for c in comps.values()]).astype(np.float32),
                95,
            )
        )
        for x, comp in comps.items():
            arm = OUT / f"w{x}" / mode
            (arm / "meshes/ink").mkdir(parents=True)
            shutil.copytree(SF, arm / "spiral-fitting", symlinks=True)
            strip = np.clip(comp.astype(np.float32) / p95, 0, 1) * 255
            Image.fromarray(strip.astype(np.uint8)).save(
                arm / "meshes/ink/crop.jpg", quality=95
            )
            (arm / "SHARED_P95").write_text(f"{p95}\n")
            print(arm)
        print(f"# {mode}: shared p95 = {p95}", file=sys.stderr)


def fg(arm: Path) -> int:
    return json.loads((arm / "ink_metric/metrics.json").read_text())["summary"][
        "total_fg_pixels"
    ]


def report(out: Path) -> None:
    f70 = {
        r["x"]: r["d_fg"]
        for r in json.loads(Path("reports/interp_windows.json").read_text())["windows"]
    }
    rows = []
    for x in windows():
        lin, smo = fg(OUT / f"w{x}" / "linear"), fg(OUT / f"w{x}" / "smooth")
        rows.append(
            {
                "x": x,
                "linear": lin,
                "smooth": smo,
                "d_shared": smo / lin - 1,
                "d_per_crop_f70": f70[x],
            }
        )
    med = lambda v: float(np.median(np.abs(v)))  # noqa: E731
    ds, dc = [r["d_shared"] for r in rows], [r["d_per_crop_f70"] for r in rows]
    summary = {
        "median_abs_d_shared": med(ds),
        "median_abs_d_per_crop": med(dc),
        "range_shared": [min(ds), max(ds)],
        "range_per_crop": [min(dc), max(dc)],
        "shared_p95": {
            m: float((OUT / f"w{windows()[0]}" / m / "SHARED_P95").read_text())
            for m in MODES
        },
    }
    held = {"median_abs_d_shared_below_2.5pct": summary["median_abs_d_shared"] < 0.025}
    out.write_text(
        json.dumps(
            {"rows": rows, "summary": summary, "prediction_held": held}, indent=2
        )
        + "\n"
    )
    for r in rows:
        print(
            f"x={r['x']:6d}  per-crop {r['d_per_crop_f70']:+.2%}   shared-p95 {r['d_shared']:+.2%}"
        )
    print(json.dumps(summary, indent=2), "\nprediction held:", held)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    r = sub.add_parser("report")
    r.add_argument("--out", type=Path, default=Path("reports/shared_p95_rescore.json"))
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    else:
        report(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
