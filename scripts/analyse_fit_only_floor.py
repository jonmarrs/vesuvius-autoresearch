"""Fit-only noise floor: the within-seed CV with the flatten made deterministic.

Implements `docs/preregistration/2026-09-21_fit_only_noise_floor.md` and nothing
else. **Written while detfit_s4 was rendering, before any arm scored.**

The rule this file exists to enforce: **a CV is never printed without its
chi-square interval.** At df=5 that interval spans roughly a factor of three,
and this project has quoted a point estimate three times (0.0125, 0.0263,
0.0536) only to watch the next arm land inside the interval it never printed.
The band is decided on the point estimate, as registered, but the interval is
on the same line, always.

Six arms are required. A partial sample is refused, not reported.
"""

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

from scipy import stats

ARMS = tuple(f"detfit_s{i}" for i in range(4, 10))
STOCK_TAGS = tuple(f"curbase_s{i}" for i in range(4, 10))
STOCK_CV = 0.0742  # the same six fits, stock flattens, df=5
INK = "total_fg_pixels"
LO, HI = 0.030, 0.055  # registered bands


def cv_ci(cv: float, df: int, alpha: float = 0.05) -> tuple[float, float]:
    return (
        cv * math.sqrt(df / stats.chi2.ppf(1 - alpha / 2, df)),
        cv * math.sqrt(df / stats.chi2.ppf(alpha / 2, df)),
    )


def fmt(cv: float, df: int) -> str:
    lo, hi = cv_ci(cv, df)
    return f"{cv:.4f}  [95% CI {lo:.4f}, {hi:.4f}]  df={df}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)

    det, stock = {}, {}
    for arm, tag in zip(ARMS, STOCK_TAGS, strict=False):
        p = so / arm / "ink_metric" / "metrics.json"
        if not p.exists():
            raise SystemExit(
                f"{arm} not scored. Six arms are required; a partial sample is "
                f"refused, not reported."
            )
        det[tag] = json.loads(p.read_text())["summary"][INK]
        stock[tag] = json.loads(
            (so / f"outer_{tag}" / "ink_metric" / "metrics.json").read_text()
        )["summary"][INK]

    vals = list(det.values())
    m = st.mean(vals)
    cv = st.stdev(vals) / m
    df = len(vals) - 1

    print("FIT-ONLY NOISE FLOOR: curbase_s4..s9 re-flattened deterministically\n")
    print(f"{'seed':<12}{'stock':>12}{'deterministic':>15}{'shift':>9}")
    for tag in STOCK_TAGS:
        d = (det[tag] - stock[tag]) / stock[tag]
        print(f"{tag:<12}{stock[tag]:>12,}{det[tag]:>15,}{d:>+9.2%}")

    print(f"\n  deterministic-flatten CV  {fmt(cv, df)}")
    print(f"  stock-flatten CV          {fmt(STOCK_CV, df)}   (same six fits)")
    lo, hi = cv_ci(cv, df)
    print(
        f"\n  The interval is the finding. A point estimate at df={df} spans a factor of "
        f"{hi / lo:.1f}."
    )

    if cv < LO:
        band, read = (
            "FLATTEN WAS MOST OF IT",
            (
                "3v3 fit comparisons become materially cheaper with FLATTEN_DETERMINISTIC=1."
            ),
        )
    elif cv <= HI:
        band, read = (
            "COMPARABLE",
            (
                "Fit RNG is comparable to the flatten. Deterministic mode helps but does not "
                "transform the design."
            ),
        )
    else:
        band, read = (
            "FIT RNG DOMINATES",
            ("The flatten's 3% was never the binding constraint on fit comparisons."),
        )
    print(f"\nBAND: {band}\n  {read}")
    print(
        f"registered prediction 1 ({LO}-{HI}): "
        f"{'MET' if LO <= cv <= HI else 'MISS, recorded as a miss'}"
    )

    top = max(det, key=det.get)
    print(
        f"\n  top deterministic scorer: {top}  "
        f"(prediction 2 was curbase_s6 -> {'MET' if top == 'curbase_s6' else 'MISS'})"
    )
    shifts = [(det[t] - stock[t]) / stock[t] for t in STOCK_TAGS]
    print(
        f"  mean det-vs-stock shift {st.mean(shifts):+.2%}, "
        f"signs {sum(s > 0 for s in shifts)}+ / {sum(s < 0 for s in shifts)}-  "
        f"(prediction 3: no particular sign)"
    )
    mde = 2.802 * cv * math.sqrt(2 / 3)
    print(
        f"\n  MDE at 3v3 from this CV: {mde:.1%}  (was {2.802 * STOCK_CV * math.sqrt(2 / 3):.1%} on stock)"
    )

    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {
                    "cv": cv,
                    "ci": [lo, hi],
                    "df": df,
                    "stock_cv": STOCK_CV,
                    "band": band,
                    "det": det,
                    "stock": stock,
                    "top": top,
                    "mde_3v3": mde,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
