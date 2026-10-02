"""POST-HOC control for docs/preregistration/2026-10-02_surface_interpolation_windows.md.

The registered windows showed smooth/linear total_fg_pixels changes of -20% to +18% per window, where the
smoke crop showed -0.09%. Before reading that as an effect of the flag: how much does the crop-level score
move under perturbations that carry no information? Each control is the LINEAR composite of a window with
one meaningless change, strip-built and scored exactly like the registered arms:

    jpeg    the linear strip decoded and re-encoded at q95 (a second lossy pass)
    noise1  +/-1 grey level on a random 8% of composite pixels (the fraction smooth changes, tiny size)
    shift1  the composite shifted one pixel right (edge column repeated)

Usage: .venv/bin/python scripts/interp_scorer_stability.py build   (then score_arms.sh on the printed dirs)
       .venv/bin/python scripts/interp_scorer_stability.py report [--out reports/interp_scorer_stability.json]
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
WIN = SO / "interp_windows"
CTRL = SO / "interp_scorer_stability"
REF_SF = SO / "detfit_up1/spiral-fitting"
WINDOWS = [77226, 83953, 56021]  # the two extremes and one moderate window
CONTROLS = ("jpeg", "noise1", "shift1")
SEED = 20261002


def composite(d: Path) -> np.ndarray:
    comp = None
    for f in sorted((d / "tif").glob("*.tif")):
        a = np.asarray(Image.open(f))
        comp = a if comp is None else np.maximum(comp, a)
    assert comp is not None
    return comp


def to_strip(comp: np.ndarray) -> np.ndarray:  # render_ink.py's normalisation, verbatim
    strip = comp.astype(np.float32)
    p95 = np.percentile(strip, 95)
    strip = np.clip(strip / p95, 0, 1) * 255 if p95 > 0 else strip
    return strip.astype(np.uint8)


def write_arm(arm: Path, strip8: np.ndarray) -> None:
    (arm / "meshes/ink").mkdir(parents=True)
    shutil.copytree(REF_SF, arm / "spiral-fitting", symlinks=True)
    Image.fromarray(strip8).save(arm / "meshes/ink/crop.jpg", quality=95)


def build() -> None:
    if CTRL.exists():
        sys.exit(f"{CTRL} exists")
    rng = np.random.default_rng(SEED)
    for x in WINDOWS:
        lin = composite(WIN / f"w{x}" / "linear")
        # jpeg: re-encode the strip the registered linear arm was scored on
        buf = io.BytesIO()
        Image.open(WIN / f"w{x}/linear/meshes/ink/crop.jpg").save(
            buf, format="JPEG", quality=95
        )
        write_arm(
            CTRL / f"w{x}" / "jpeg", np.asarray(Image.open(io.BytesIO(buf.getvalue())))
        )
        # noise1: +/-1 on 8% of composite pixels, valid pixels only, clipped to uint8
        noisy = lin.astype(np.int16)
        pick = (rng.random(lin.shape) < 0.08) & (lin > 0)
        noisy[pick] += rng.choice(
            np.array([-1, 1], dtype=np.int16), size=int(pick.sum())
        )
        write_arm(
            CTRL / f"w{x}" / "noise1", to_strip(np.clip(noisy, 0, 255).astype(np.uint8))
        )
        # shift1: one pixel right
        sh = np.concatenate([lin[:, :1], lin[:, :-1]], axis=1)
        write_arm(CTRL / f"w{x}" / "shift1", to_strip(sh))
        for c in CONTROLS:
            print(CTRL / f"w{x}" / c)


def fg(arm: Path) -> int:
    return json.loads((arm / "ink_metric/metrics.json").read_text())["summary"][
        "total_fg_pixels"
    ]


def report(out: Path) -> None:
    rows = []
    for x in WINDOWS:
        base = fg(WIN / f"w{x}" / "linear")
        row = {"x": x, "linear": base, "smooth": fg(WIN / f"w{x}" / "smooth")}
        row["d_smooth"] = row["smooth"] / base - 1
        for c in CONTROLS:
            row[c] = fg(CTRL / f"w{x}" / c)
            row[f"d_{c}"] = row[c] / base - 1
        rows.append(row)
        print(
            f"x={x}: smooth {row['d_smooth']:+.2%}   "
            + "   ".join(f"{c} {row[f'd_{c}']:+.2%}" for c in CONTROLS)
        )
    out.write_text(
        json.dumps({"post_hoc": True, "seed": SEED, "rows": rows}, indent=2) + "\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    r = sub.add_parser("report")
    r.add_argument(
        "--out", type=Path, default=Path("reports/interp_scorer_stability.json")
    )
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    else:
        report(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
