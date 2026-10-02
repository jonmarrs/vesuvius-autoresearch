"""docs/preregistration/2026-10-02_surface_interpolation_windows.md -- select, build, analyse.

select            print the 8 registered window x-offsets (coverage only; never ink or outputs)
strip ARM TIFDIR  build ARM/meshes/ink/crop.jpg from TIFDIR exactly as render_ink.py builds a strip,
                  and give ARM the pinned scorer tree
analyse [--out]   per-window and summary deltas, checked against the registered predictions
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
REF = SO / "detfit_up1"
PUBLISHED_SLICE = REF / "meshes/concat/w120-129_flat/ink/02.tif"
OUT = SO / "interp_windows"
WIDTH, HEIGHT, X_STEP = 2048, 4460, 512
X_LO, N_SECTORS = (
    32768,
    8,
)  # 8 equal sectors over [X_LO, strip width); window fully inside


def select_windows() -> list[int]:
    a = tifffile.imread(PUBLISHED_SLICE) > 0  # 404 Mpx: PIL refuses it as a bomb
    h, w = a.shape
    assert h == HEIGHT, f"published render height {h} != registered {HEIGHT}"
    cols = a.sum(axis=0).astype(np.int64)
    csum = np.concatenate([[0], np.cumsum(cols)])
    edges = [X_LO + (w - X_LO) * i // N_SECTORS for i in range(N_SECTORS + 1)]
    chosen = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=False):
        best = None
        for x in range(lo, hi - WIDTH + 1, X_STEP):
            cov = (csum[x + WIDTH] - csum[x]) / (WIDTH * h)
            if best is None or cov > best[0]:  # ties keep the smaller x
                best = (cov, x)
        if best is not None:
            chosen.append(best[1])
    return chosen


def max_composite(
    paths: list[Path],
) -> np.ndarray:  # the pinned render_ink.max_composite, verbatim
    comp = None
    for p in paths:
        layer = np.asarray(Image.open(p))
        comp = layer if comp is None else np.maximum(comp, layer)
    assert comp is not None, "no slices"
    return comp


def build_strip(arm: Path, tifdir: Path) -> None:
    tifs = sorted(tifdir.glob("*.tif"))
    if len(tifs) != 5:
        sys.exit(f"{tifdir}: {len(tifs)} tifs, expected 5")
    (arm / "meshes/ink").mkdir(parents=True)
    shutil.copytree(REF / "spiral-fitting", arm / "spiral-fitting", symlinks=True)
    strip = max_composite(tifs).astype(np.float32)
    p95 = np.percentile(strip, 95)
    strip = np.clip(strip / p95, 0, 1) * 255 if p95 > 0 else strip
    Image.fromarray(strip.astype(np.uint8)).save(
        arm / "meshes/ink/crop.jpg", quality=95
    )
    print(f"strip {arm.name}: p95={p95} shape={strip.shape}")


def _metrics(arm: Path) -> dict:
    d = json.loads((arm / "ink_metric/metrics.json").read_text())
    s, row = d["summary"], d["strips"][0]
    return {
        "fg": s["total_fg_pixels"],
        "line": s["overall_line_score"],
        "line_gaps": row["line_gap_count"],
        "col": s["overall_column_score"],
    }


def analyse(out: Path) -> int:
    xs = select_windows()
    rows = []
    for x in xs:
        lin, smo = (
            _metrics(OUT / f"w{x}" / "linear"),
            _metrics(OUT / f"w{x}" / "smooth"),
        )
        rows.append({
            "x": x,
            "linear": lin,
            "smooth": smo,
            "d_fg": smo["fg"] / lin["fg"] - 1 if lin["fg"] else None,
            "d_line": smo["line"] - lin["line"],
        })  # fmt: skip
    d_fg = [r["d_fg"] for r in rows]
    d_line = [r["d_line"] for r in rows]
    summary = {
        "n_windows": len(rows),
        "d_fg_median": float(np.median(d_fg)),
        "d_fg_range": [min(d_fg), max(d_fg)],
        "d_fg_pos": sum(v > 0 for v in d_fg),
        "d_fg_neg": sum(v < 0 for v in d_fg),
        "d_line_median": float(np.median(d_line)),
        "d_line_range": [min(d_line), max(d_line)],
        "d_line_pos": sum(v > 0 for v in d_line),
        "d_line_neg": sum(v < 0 for v in d_line),
        "min_line_gaps": min(
            min(r["linear"]["line_gaps"], r["smooth"]["line_gaps"]) for r in rows
        ),
    }
    predictions = {
        "fg_abs_below_1pct_every_window": all(abs(v) < 0.01 for v in d_fg),
        "line_no_consistent_direction": not (
            summary["d_line_pos"] == len(rows) or summary["d_line_neg"] == len(rows)
        ),  # fmt: skip
    }
    res = {"windows": rows, "summary": summary, "predictions_held": predictions}
    out.write_text(json.dumps(res, indent=2) + "\n")
    for r in rows:
        print(f"x={r['x']:6d}  fg {r['linear']['fg']:>8} -> {r['smooth']['fg']:>8}  {r['d_fg']:+.4%}   "
              f"line {r['linear']['line']:.3f} -> {r['smooth']['line']:.3f} "
              f"(gaps {r['linear']['line_gaps']}/{r['smooth']['line_gaps']})")  # fmt: skip
    print(json.dumps(summary, indent=2))
    print("predictions held:", predictions)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select")
    s = sub.add_parser("strip")
    s.add_argument("arm", type=Path)
    s.add_argument("tifdir", type=Path)
    a = sub.add_parser("analyse")
    a.add_argument("--out", type=Path, default=Path("reports/interp_windows.json"))
    args = ap.parse_args()
    if args.cmd == "select":
        print("\n".join(map(str, select_windows())))
        return 0
    if args.cmd == "strip":
        build_strip(args.arm, args.tifdir)
        return 0
    return analyse(args.out)


if __name__ == "__main__":
    sys.exit(main())
