"""Is the flatten's per-block rescoring RE-SAMPLING, or does it need DISTORTION?

Implements `docs/preregistration/2026-09-23_resampling_or_distortion.md`.
**Written before either arm was rendered.**

Two flattens of one surface are re-read ~0.135 (ink-weighted sd per 2048-px
block), and a rigid translation re-reads ~0.0001. This re-samples the SAME
layout by half a strip pixel (t = 0.05 cell, primary arm) and compares
per-block rescoring against the 0 vx surface it came from. A secondary arm
(t = 0.5 cell = 5 px, a translation plus the re-interpolated surface) is reported
descriptively.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_layout_rescoring import compare  # noqa: E402

ZERO = "flat_study_zero"
PRIMARY = "rs_t005"  # t = 0.05 cell = half a strip pixel: re-sampling, layout fixed
SECONDARY = "rs_t05"  # t = 0.5 cell = 5 px: translation + re-interpolated surface
REF = 0.135  # rad0 vs rad0b, the flatten's own re-layout
LO, HI = 0.02, 0.07  # registered bands on the primary arm's sd at 2048 px
BLOCK = 2048


PX_PER_CELL = 10  # strip pixels per flat-grid cell at this render scale
T = {PRIMARY: 0.05, SECONDARY: 0.5}
TRIM_RE = re.compile(r"rect c=(\d+)\+\d+ r=(\d+)\+\d+")


def parse_trim(render_log: Path) -> tuple[int, int]:
    """(c, r): cells the render trimmed from the left and top of the grid. The
    re-sampled arms lose border columns, so their strip starts c cells later than
    the reference's. Unaligned, a 10 px offset alone fakes a per-block sd of 0.013
    (measured on the reference's own masks) -- the amendment of 2026-09-23."""
    m = None
    for line in Path(render_log).read_text(errors="replace").splitlines():
        hit = TRIM_RE.search(line)
        if hit:
            m = hit
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def fg_columns(arm_dir: Path, rows: tuple[int, int] | None = None) -> np.ndarray:
    """Ink pixels per strip column, optionally over rows [r0, r1) only."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    masks = sorted(
        (Path(arm_dir) / "ink_metric" / "predictions").glob("*_mask*.png"),
        key=lambda p: int(re.search(r"\.(\d+)$", p.stem).group(1))
        if re.search(r"\.(\d+)$", p.stem)
        else -1,
    )
    cols = []
    for p in masks:
        k = np.asarray(Image.open(p))
        k = (k[..., 0] if k.ndim == 3 else k) > 0
        if rows is not None:
            k = k[rows[0] : rows[1]]
        cols.append(k.sum(0))
    return np.concatenate(cols).astype(float)


def aligned_block_sd(
    ref: np.ndarray, arm: np.ndarray, offset: int, block: int = BLOCK
) -> float:
    """Ink-weighted sd of the per-block relative change, comparing arm column k
    with reference column k + offset."""
    r = ref[offset : offset + len(arm)]
    a = arm[: len(r)]
    n = len(a) // block
    br = r[: n * block].reshape(n, block).sum(1)
    ba = a[: n * block].reshape(n, block).sum(1)
    ok = br > 0
    d = (ba[ok] - br[ok]) / br[ok]
    w = br[ok] / br[ok].sum()
    return float(np.sqrt(np.average((d - np.average(d, weights=w)) ** 2, weights=w)))


def verdict(sd: float) -> tuple[str, str]:
    if sd >= HI:
        return "RE-SAMPLING SUFFICES", (
            "Moving every sample half a pixel, with the layout fixed, re-draws at least half "
            "the flatten's per-block rescoring: no distortion is needed to explain it."
        )
    if sd <= LO:
        return "DISTORTION REQUIRED", (
            "Re-sampling alone re-draws little; the flatten's per-block rescoring needs the "
            "layout itself to change (stretch or shear)."
        )
    return (
        "BOTH CONTRIBUTE",
        "Re-sampling explains part of the rescoring, not most of it.",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)
    for arm in (PRIMARY, SECONDARY):
        if not (so / arm / "ink_metric" / "metrics.json").exists():
            raise SystemExit(f"{arm} not scored -- refused, not reported.")
    shas = {
        (so / x / "VILLA_SHA").read_text().strip() for x in (ZERO, PRIMARY, SECONDARY)
    }
    if len(shas) != 1:
        print("VERDICT: VOID -- the arms do not share one tree.")
        return 1

    out = {}
    print("RE-SAMPLING OR DISTORTION? same layout, sample points moved in-plane\n")
    for arm in (PRIMARY, SECONDARY):
        r = compare(so / ZERO, so / arm, blocks=(BLOCK,))
        b = r["block"][BLOCK]
        c, rr = parse_trim(so / f"{arm}.render.log")
        arm_cols = fg_columns(so / arm)
        from PIL import Image

        first = sorted((so / arm / "ink_metric" / "predictions").glob("*_mask*.png"))[0]
        h = Image.open(first).size[1]
        ref_cols = fg_columns(so / ZERO, rows=(rr * PX_PER_CELL, rr * PX_PER_CELL + h))
        offset = c * PX_PER_CELL + round(T[arm] * PX_PER_CELL)
        sd_al = aligned_block_sd(ref_cols, arm_cols, offset)
        out[arm] = {
            "covered_ratio": r["covered_ratio"],
            "fg_ratio": r["fg_ratio"],
            "density_ratio": r["density_ratio"],
            "sd_2048_unaligned": b["sd"],
            "trim_c_r": [c, rr],
            "offset_px": offset,
            "sd_2048": sd_al,
            "lag1_unaligned": b["lag1"],
        }
        print(
            f"  {arm:<8} covered {r['covered_ratio']:.4f}  ink {r['fg_ratio']:.4f}  "
            f"per-block sd ALIGNED {sd_al:.4f} (offset {offset} px, trim c={c} r={rr}; "
            f"unaligned {b['sd']:.4f})  [re-layout ref {REF}, translation ~0.0001]"
        )
    sd = out[PRIMARY]["sd_2048"]
    v, read = verdict(sd)
    print(
        f"\nVERDICT (primary, {PRIMARY}, sd {sd:.4f}; bands {LO} / {HI}): {v}\n  {read}"
    )
    print(f"  secondary {SECONDARY} (descriptive): sd {out[SECONDARY]['sd_2048']:.4f}")
    out["verdict"] = v
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
