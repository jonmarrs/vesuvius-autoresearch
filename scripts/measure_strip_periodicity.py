"""Measure the dominant column-scale periodicity of a rendered ink strip.

Written 2026-09-03 to replace an inline analysis that produced a retracted
finding (`reports/column_structure_is_absent_outer_not_missegmented.md`). It is a
file with tests rather than a heredoc because that is exactly the difference
between the committed tools here, which all have known-input controls, and the
throwaway code the retraction came from.

Two defects in the retracted version, both from one line
(`hp = min(2500, p.size // 8)`):

* it trimmed 2*hp points off the profile, which on an 8,810 px inner strip left
  3,810 of them and destroyed the frequency resolution the measurement needed;
* hp scaled with strip length for short strips and not for long ones, so inner and
  outer strips were filtered differently and the difference was read as data.

This version uses a linear detrend and a zero-padded FFT, no moving-average
high-pass and no trimming, and `validate()` demonstrates on synthetic input that it
recovers known periods at both real strip lengths before it is pointed at a strip.
"""

import argparse
import glob
import os
import sys

import numpy as np

PAD = 8  # FFT zero-padding factor: refines the frequency grid
BAND = (150.0, 1500.0)  # periods (px) worth reporting for column-scale structure


def column_profile(ink_dir: str) -> np.ndarray:
    """Column-mean ink over the whole strip. Column means are separable, so
    computing per tile and concatenating is exact for the joined strip."""
    tiles = sorted(glob.glob(os.path.join(ink_dir, "*_flat*.jpg")))
    if not tiles:
        raise SystemExit(f"no *_flat*.jpg tiles in {ink_dir}")
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    cols = []
    for t in tiles:
        a = np.asarray(Image.open(t).convert("L")).astype(np.float32)
        cols.append(a.mean(axis=0))
        del a
    return np.concatenate(cols)


def dominant_period(
    p: np.ndarray, band: tuple[float, float] = BAND, pad: int = PAD
) -> tuple[float, float]:
    """Return (period_px, share_of_band_power) for the strongest line in `band`.

    Linear detrend only. A moving-average high-pass is deliberately NOT used: it
    both trims the series and, if its window is chosen relative to length, filters
    different strips differently.
    """
    n = p.size
    x = p - np.polyval(np.polyfit(np.arange(n), p, 1), np.arange(n))
    x = x * np.hanning(n)
    F = np.abs(np.fft.rfft(x, n * pad)) ** 2
    f = np.fft.rfftfreq(n * pad)
    per = np.divide(1.0, f, out=np.full(F.shape, np.inf), where=f > 0)
    m = (per >= band[0]) & (per <= band[1])
    if not m.any():
        return float("nan"), 0.0
    peak = float(per[m][np.argmax(F[m])])
    share = float(F[m].max() / F[m].sum())
    return peak, share


def validate(verbose: bool = True) -> bool:
    """Known-input control. Recover synthetic periods at BOTH real strip lengths.

    This is the check the retracted analysis never had. It must pass before any
    number this script prints about a real strip means anything.
    """
    ok = True
    rows = []
    for length in (8810, 82670):
        for true in (300.0, 850.0, 945.0):
            got = []
            for seed in range(5):
                r = np.random.default_rng(seed)
                t = np.arange(length)
                sig = np.sin(2 * np.pi * t / true) + 0.5 * r.normal(size=length)
                got.append(dominant_period(sig)[0])
            err = max(abs(g - true) / true for g in got)
            good = err < 0.03
            ok &= good
            rows.append((length, true, float(np.mean(got)), err, good))
    if verbose:
        print(f"{'length':>9}{'true':>8}{'recovered':>11}{'max err':>9}   control")
        for length, true, mean, err, good in rows:
            print(
                f"{length:>9}{true:>8.0f}{mean:>11.1f}{100 * err:>8.1f}%   "
                f"{'ok' if good else 'FAIL'}"
            )
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ink_dirs", nargs="*", help="<arm>/meshes/ink directories")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    if not validate():
        print(
            "\nCONTROL FAILED: the estimator does not recover known periods. "
            "Nothing it says about a real strip is usable."
        )
        return 1
    print()
    if args.validate_only:
        return 0

    for d in args.ink_dirs:
        p = column_profile(d)
        peak, share = dominant_period(p)
        print(
            f"{os.path.basename(os.path.dirname(os.path.dirname(d))):<22}"
            f"width {p.size:>7}  dominant {peak:>7.0f} px  "
            f"({100 * share:.1f}% of band power)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
