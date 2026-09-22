"""Pooled fit-only noise floor across three current-tier configs.

Implements `docs/preregistration/2026-09-22_pooled_fit_only_floor.md`. **Written
while detfit_ns1 was still flattening**, before any arm of this study scored.

Why pooled WITHIN-group and not a CV of all twelve: the three configs sit at
different means and answer different manipulations, so between-group spread is
signal. Pooling relative deviations within each group is the one-way ANOVA step
written out, the same estimator `measure_noise_floor.py` uses.

Two rules this file enforces structurally:

* **A CV is never printed without its chi-square interval.** At df=11 that
  interval still spans 2.4x. Three published floors were retracted after being
  quoted as bare point estimates.
* **The failure branch refuses to pool across instruments.** If the twelve arms
  do not share one VILLA_SHA and one RENDER_IMAGE image_id, no pooled figure is
  emitted -- a floor pooled across instruments is not a floor.
"""

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

from scipy import stats

GROUPS = {
    "curbase": [f"detfit_s{i}" for i in range(4, 10)],
    "nosamecur": ["detfit_ns1", "detfit_ns2", "detfit_ns3"],
    "anchor10cov": ["detfit_an1", "detfit_an2", "detfit_an3"],
}
STOCK = {
    "curbase": [f"outer_curbase_s{i}" for i in range(4, 10)],
    "nosamecur": [f"outer_nosamecur_s{i}" for i in (1, 2, 3)],
    "anchor10cov": [
        "outer_anchor10cov_pilot",
        "outer_anchor10cov_s2",
        "outer_anchor10cov_s3",
    ],
}
INK = "total_fg_pixels"
LO, HI = 0.055, 0.075  # registered band boundaries
PRED_LO, PRED_HI = 0.040, 0.075  # registered prediction 1


def ink(so: Path, arm: str) -> float:
    p = so / arm / "ink_metric" / "metrics.json"
    if not p.exists():
        raise SystemExit(
            f"{arm} not scored. All twelve arms are required; a partial sample is "
            f"refused, not reported."
        )
    return json.loads(p.read_text())["summary"][INK]


def provenance(so: Path, arms: list[str]) -> tuple[set[str], set[str]]:
    shas, imgs = set(), set()
    for a in arms:
        shas.add((so / a / "VILLA_SHA").read_text().strip())
        ri = (so / a / "RENDER_IMAGE").read_text()
        imgs.add(
            next(
                ln.split("=", 1)[1]
                for ln in ri.splitlines()
                if ln.startswith("image_id=")
            )
        )
    return shas, imgs


def pooled_cv(by_group: dict[str, list[float]]) -> tuple[float, int]:
    devs, df = [], 0
    for v in by_group.values():
        if len(v) < 2:
            continue
        m = st.mean(v)
        devs += [(x - m) / m for x in v]
        df += len(v) - 1
    return (sum(d * d for d in devs) / df) ** 0.5, df


def ci(cv: float, df: int, alpha: float = 0.05) -> tuple[float, float]:
    return (
        cv * math.sqrt(df / stats.chi2.ppf(1 - alpha / 2, df)),
        cv * math.sqrt(df / stats.chi2.ppf(alpha / 2, df)),
    )


def fmt(cv: float, df: int) -> str:
    lo, hi = ci(cv, df)
    return f"{cv:.4f}  [95% CI {lo:.4f}, {hi:.4f}]  df={df}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)
    all_arms = [x for g in GROUPS.values() for x in g]

    shas, imgs = provenance(so, all_arms)
    print("POOLED FIT-ONLY FLOOR: three configs, flatten held deterministic\n")
    print(
        f"  provenance: {len(shas)} distinct VILLA_SHA, {len(imgs)} distinct image_id"
    )
    if len(shas) != 1 or len(imgs) != 1:
        print("\nVERDICT: NOT POOLED -- the arms do not share one instrument.")
        print(
            "  A floor pooled across instruments is not a floor. Registered failure branch."
        )
        return 1
    print("  -> one tree, one image: pooling is legitimate\n")

    det = {g: [ink(so, x) for x in arms] for g, arms in GROUPS.items()}
    stock = {g: [ink(so, x) for x in arms] for g, arms in STOCK.items()}

    print(f"{'group':<14}{'n':>3}{'det mean':>13}{'det CV':>9}{'stock CV':>10}")
    for g in GROUPS:
        d, s = det[g], stock[g]
        print(
            f"{g:<14}{len(d):>3}{st.mean(d):>13,.0f}"
            f"{st.stdev(d) / st.mean(d):>9.4f}{st.stdev(s) / st.mean(s):>10.4f}"
        )

    cv, df = pooled_cv(det)
    scv, sdf = pooled_cv(stock)
    print(f"\n  POOLED fit-only CV   {fmt(cv, df)}")
    print(f"  pooled stock CV      {fmt(scv, sdf)}   (same twelve fits)")
    print(
        f"  curbase alone        {fmt(st.stdev(det['curbase']) / st.mean(det['curbase']), 5)}"
    )

    if cv < LO:
        band, read = (
            "CURBASE WAS UNREPRESENTATIVE",
            (
                "The tier floor is better than 20%. Quote the pooled figure for current-tier designs."
            ),
        )
    elif cv <= HI:
        band, read = (
            "BETWEEN",
            (
                "The tier sits between the quiet groups and curbase; curbase-based designs were "
                "conservative. Quote the pooled figure."
            ),
        )
    else:
        band, read = (
            "CURBASE WAS REPRESENTATIVE",
            (
                "~20% at 3v3 stands as the current-tier floor. Fit comparisons are expensive, full stop."
            ),
        )
    print(f"\nBAND: {band}\n  {read}")
    met = PRED_LO <= cv <= PRED_HI
    print(
        f"registered prediction 1 ({PRED_LO}-{PRED_HI}): "
        f"{'MET' if met else 'MISS, recorded as a miss'}"
    )

    noisiest = max(det, key=lambda g: st.stdev(det[g]) / st.mean(det[g]))
    print(
        f"prediction 2 (curbase stays noisiest): "
        f"{'MET' if noisiest == 'curbase' else f'MISS -- {noisiest} is'}"
    )
    print(
        "prediction 3: significance WITHHELD by registration; df=2 groups establish nothing."
    )

    mde = 2.802 * cv * math.sqrt(2 / 3)
    print(f"\n  MDE at 3v3 from the pooled CV: {mde:.1%}  (curbase alone gave 20.8%)")

    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {
                    "pooled_cv": cv,
                    "ci": list(ci(cv, df)),
                    "df": df,
                    "stock_pooled_cv": scv,
                    "band": band,
                    "prediction1_met": met,
                    "noisiest": noisiest,
                    "mde_3v3": mde,
                    "det": det,
                    "stock": stock,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
