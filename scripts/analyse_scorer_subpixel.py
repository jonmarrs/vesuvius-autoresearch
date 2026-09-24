"""Does the scorer alone amplify a half-pixel re-sample?

Implements `docs/preregistration/2026-09-24_scorer_subpixel.md`. **Written before the
arm was built or scored.**

`rs_t005` (a rendered half-pixel re-sample, layout fixed) re-drew 0.088 per 2 kpx
block against `flat_study_zero`. `sp_half` is `flat_study_zero`'s own pixels
interpolated half a pixel along x, with no render. If it re-draws most of 0.088,
the scorer amplifies sub-pixel image changes; if little, the sensitivity lives in
how the render samples the volume.

Also reports, descriptively, how much the PIXELS change in both arms.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_resampling_or_distortion import (  # noqa: E402
    aligned_block_sd,
    fg_columns,
    parse_trim,
)
from build_shifted_strip_arm import load_strip  # noqa: E402

ZERO, ARM, RENDERED = "flat_study_zero", "sp_half", "rs_t005"
RENDERED_SD = 0.0882  # reports/re_sampling_is_enough.md
LO, HI = 0.02, 0.06


def verdict(sd: float) -> tuple[str, str]:
    if sd >= HI:
        return "SCORER AMPLIFIES", (
            "The strip's own pixels, moved half a pixel with no render, re-draw most of what the "
            "rendered re-sample did: the scorer turns sub-pixel image changes into block-level ink."
        )
    if sd <= LO:
        return "RENDER-SIDE", (
            "An image-level half-pixel shift re-draws little; the rendered re-sample's effect comes "
            "from how the volume is sampled, not from the scorer's response to sub-pixel shifts."
        )
    return (
        "BOTH",
        "The scorer amplifies part of it; the render's sampling contributes the rest.",
    )


def pixel_stats(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    m = (a > 8) | (b > 8)
    d = np.abs(a[m].astype(np.int16) - b[m].astype(np.int16))
    r = float(np.corrcoef(a[m].astype(float), b[m].astype(float))[0, 1])
    return {
        "mean_abs_diff": float(d.mean()),
        "p90_abs_diff": float(np.percentile(d, 90)),
        "r": r,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)
    if not (so / ARM / "ink_metric" / "metrics.json").exists():
        raise SystemExit(f"{ARM} not scored -- refused, not reported.")

    zero_cols = fg_columns(so / ZERO)
    arm_cols = fg_columns(so / ARM)
    sd = aligned_block_sd(zero_cols, arm_cols, 0)

    def ink(d: str) -> int:
        m = json.loads((so / d / "ink_metric" / "metrics.json").read_text())
        return m["summary"]["total_fg_pixels"]

    print(
        "SCORER SUB-PIXEL: the reference's own pixels, moved half a pixel, no render\n"
    )
    print(
        f"  {ARM}: per-block sd {sd:.4f}  ink {ink(ARM) / ink(ZERO):.4f}  "
        f"(rendered half-pixel {RENDERED}: {RENDERED_SD}; whole-pixel moves ~0.0001)"
    )

    z = load_strip(so / ZERO / "meshes" / "ink")
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    h = np.asarray(Image.open(so / ARM / "meshes" / "ink" / "w120-129_flat.png"))
    ps_arm = pixel_stats(z, h)
    c, r = parse_trim(so / f"{RENDERED}.render.log")
    rend = load_strip(so / RENDERED / "meshes" / "ink")
    off = c * 10
    zz = z[r * 10 : r * 10 + rend.shape[0], off : off + rend.shape[1]]
    ps_rend = pixel_stats(zz, rend[:, : zz.shape[1]])
    print(
        f"\n  pixels, image half-pixel vs reference:    mean |d| {ps_arm['mean_abs_diff']:.2f}  "
        f"p90 {ps_arm['p90_abs_diff']:.0f}  r {ps_arm['r']:.4f}"
    )
    print(
        f"  pixels, RENDERED half-pixel vs reference: mean |d| {ps_rend['mean_abs_diff']:.2f}  "
        f"p90 {ps_rend['p90_abs_diff']:.0f}  r {ps_rend['r']:.4f}  (aligned {off} px)"
    )

    v, read = verdict(sd)
    print(f"\nVERDICT (sd {sd:.4f}; bands {LO} / {HI}): {v}\n  {read}")
    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {
                    "sd_2048": sd,
                    "ink_ratio": ink(ARM) / ink(ZERO),
                    "pixels_image": ps_arm,
                    "pixels_rendered": ps_rend,
                    "verdict": v,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
