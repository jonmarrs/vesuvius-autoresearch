"""docs/preregistration/2026-10-02_surface_interpolation_windows.md -- select, build, analyse.

select            print the 8 registered window x-offsets (coverage only; never ink or outputs)
strip ARM TIFDIR  build ARM/meshes/ink/crop.jpg from TIFDIR exactly as render_ink.py builds a strip,
                  and give ARM the pinned scorer tree
analyse [--out]   per-window and summary deltas, checked against the registered predictions
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import tifffile
from PIL import Image

if TYPE_CHECKING or __package__:
    from .interpolation_inputs import read_slices
else:
    from interpolation_inputs import read_slices

SO = Path(os.environ.get("SO", "/home/jon/openclaw-workspace/Neo-VM/spiral_out"))
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
    if h != HEIGHT:
        raise ValueError(f"published render height {h} != registered {HEIGHT}")
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
    if len(chosen) != N_SECTORS:
        raise ValueError(f"expected {N_SECTORS} full windows, found {len(chosen)}")
    return chosen


def build_strip(arm: Path, tifdir: Path) -> None:
    layers = read_slices(tifdir, shape=(HEIGHT, WIDTH))
    strip = np.maximum.reduce(layers).astype(np.float32)
    p95 = np.percentile(strip, 95)
    strip = np.clip(strip / p95, 0, 1) * 255 if p95 > 0 else strip
    (arm / "meshes/ink").mkdir(parents=True)
    shutil.copytree(REF / "spiral-fitting", arm / "spiral-fitting", symlinks=True)
    Image.fromarray(strip.astype(np.uint8)).save(
        arm / "meshes/ink/crop.jpg", quality=95
    )
    print(f"strip {arm.name}: p95={p95} shape={strip.shape}")


def _metrics(arm: Path) -> dict:
    d = json.loads((arm / "ink_metric/metrics.json").read_text())
    if not isinstance(d, dict) or not isinstance(d.get("summary"), dict):
        raise ValueError(f"{arm}: missing metrics summary")
    strips = d.get("strips")
    if (
        not isinstance(strips, list)
        or len(strips) != 1
        or not isinstance(strips[0], dict)
    ):
        raise ValueError(f"{arm}: expected exactly one scored crop")
    s, row = d["summary"], strips[0]
    total, foreground, gaps = (
        s.get("total_pixels"),
        s.get("total_fg_pixels"),
        row.get("line_gap_count"),
    )
    if type(total) is not int or total != WIDTH * HEIGHT:
        raise ValueError(f"{arm}: total_pixels does not match the registered crop area")
    if type(foreground) is not int or not 0 <= foreground <= total:
        raise ValueError(f"{arm}: invalid foreground count")
    if row.get("total_pixels") != total or row.get("fg_pixels") != foreground:
        raise ValueError(f"{arm}: inconsistent summary and strip counts")
    if type(gaps) is not int or gaps < 0:
        raise ValueError(f"{arm}: invalid line gap count")
    for name in ("overall_line_score", "overall_column_score"):
        value = s.get(name)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise ValueError(f"{arm}: {name} must be finite")
    return {
        "fg": s["total_fg_pixels"],
        "line": s["overall_line_score"],
        "line_gaps": row["line_gap_count"],
        "col": s["overall_column_score"],
    }


def analyse(out: Path) -> int:
    xs = select_windows()
    recorded = [int(value) for value in (OUT / "WINDOWS").read_text().split()]
    if len(xs) != N_SECTORS or len(set(recorded)) != N_SECTORS or recorded != xs:
        raise ValueError(
            f"WINDOWS does not match the {N_SECTORS} registered coverage selections"
        )
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
    d_fg = [r["d_fg"] for r in rows if r["d_fg"] is not None]
    d_line = [r["d_line"] for r in rows]
    summary = {
        "n_windows": len(rows),
        "d_fg_median": float(np.median(d_fg)) if d_fg else None,
        "d_fg_range": [min(d_fg), max(d_fg)] if d_fg else None,
        "n_fg_undefined": len(rows) - len(d_fg),
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
        "fg_abs_below_1pct_every_window": all(abs(v) < 0.01 for v in d_fg)
        if len(d_fg) == len(rows)
        else None,
        "line_no_consistent_direction": not (
            summary["d_line_pos"] == len(rows) or summary["d_line_neg"] == len(rows)
        ),  # fmt: skip
    }
    res = {"windows": rows, "summary": summary, "predictions_held": predictions}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, allow_nan=False) + "\n")
    for r in rows:
        delta = (
            f"{r['d_fg']:+.4%}" if r["d_fg"] is not None else "undefined (linear fg=0)"
        )
        print(f"x={r['x']:6d}  fg {r['linear']['fg']:>8} -> {r['smooth']['fg']:>8}  {delta}   "
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
