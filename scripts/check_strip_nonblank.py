"""Enforce the registered non-blank control on a rendered ink strip.

Every outer-winding pre-registration in this work carries the same control: the
strip must render non-blank (`p95 > 0`), because an unscaled or misconfigured
render exits 0 and writes an entirely BLACK strip, reported only as `p95=0.0` in
passing (see repro/spiral_render/README.md section 3). A blank arm would then be
scored as "no ink" rather than "no render", which is the worst kind of failure:
silent, plausible, and in the direction of a null.

Until now that control was checked by hand, which means it was checked when I
remembered. This runs it.

The rule, matching how every arm in this study was judged:
  * the FULL tiles must have p95 > 0;
  * the last tile is exempt from p95 (it is a narrow sliver, mostly padding, and
    has legitimately read p95 = 0 in every arm measured, with p99 around 253);
  * the strip as a whole must have a plausible nonzero fraction (advisory: this
    warns, it does not void).

KNOWN LIMITATION: `p95 > 0` cannot separate "sparse ink" from "no render". A strip
that is only a few percent inked has p95 = 0 and is voided as BLANK even though it
carries signal. That is safe HERE only because every measured arm sits at 44.8% to
47.2% nonzero, nowhere near the boundary. A future ROI that renders genuinely
sparse strips would need this control re-specified before it is trusted, because
it would void real data.

Usage:
    check_strip_nonblank.py <arm_dir_or_ink_dir> [...]
"""

import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# The four measured arms ran 44.8% to 47.2% nonzero. A strip far outside that is
# not necessarily wrong, but it is not the thing the other arms are, so say so.
NONZERO_LO = 0.20
NONZERO_HI = 0.80

# A sliver narrower than this is treated as the padding tile and exempted from
# the p95 rule. Real tiles in this study are 16,384 px wide.
SLIVER_MAX_WIDTH = 4000


def ink_dir(path: str) -> str:
    if os.path.isdir(os.path.join(path, "meshes", "ink")):
        return os.path.join(path, "meshes", "ink")
    return path


def check(path: str) -> tuple[bool, list[str]]:
    d = ink_dir(path)
    tiles = sorted(glob.glob(os.path.join(d, "*_flat*.jpg")))
    notes: list[str] = []
    if not tiles:
        return False, [f"no *_flat*.jpg tiles in {d}"]

    total = nonzero = 0
    ok = True
    for t in tiles:
        arr = np.asarray(Image.open(t).convert("L"))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
        h, w = arr.shape
        total += arr.size
        nonzero += int((arr > 0).sum())
        sliver = w < SLIVER_MAX_WIDTH
        tag = "sliver" if sliver else "full"
        verdict = "ok"
        if p95 <= 0 and not sliver:
            verdict = "BLANK"
            ok = False
        elif p95 <= 0 and sliver:
            verdict = "ok (sliver exempt)" if p99 > 0 else "BLANK sliver"
            if p99 <= 0:
                ok = False
        notes.append(
            f"  {os.path.basename(t):<26} {w}x{h:<6} {tag:<7} p95={p95:6.1f} "
            f"p99={p99:6.1f}  {verdict}"
        )
        del arr

    frac = nonzero / total if total else 0.0
    notes.append(f"  strip: {total:,} px, nonzero {100 * frac:.1f}%")
    if not (NONZERO_LO <= frac <= NONZERO_HI):
        notes.append(
            f"  WARNING nonzero {100 * frac:.1f}% outside the {100 * NONZERO_LO:.0f}-"
            f"{100 * NONZERO_HI:.0f}% seen in every measured arm"
        )
    return ok, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+")
    args = ap.parse_args()

    failed = []
    for a in args.arms:
        ok, notes = check(a)
        print(f"{os.path.basename(os.path.normpath(a))}: {'PASS' if ok else 'FAIL'}")
        for n in notes:
            print(n)
        if not ok:
            failed.append(a)

    if failed:
        print(
            f"\nCONTROL FAILED for {len(failed)} arm(s). A blank strip means a render "
            "fault, not absent ink; the arm is VOID and must not be scored."
        )
        return 1
    print("\nregistered non-blank control: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
