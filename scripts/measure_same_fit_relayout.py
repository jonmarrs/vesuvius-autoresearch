"""How much does re-laying out ONE fit move total_fg_pixels? (layout-only noise)

Each `curbase` fit exists flattened twice: stock (`outer_curbase_sN`) and
deterministic (`detfit_sN`). Same fit, same meshes, same surface; only the
layout differs. The spread of ln(det / stock) across the six fits is the
layout-only noise on the count, which the one-pair block model in
`reports/the_flatten_noise_is_local_rescoring.md` predicted at 0.026-0.030.

    python scripts/measure_same_fit_relayout.py [--spiral-out DIR] [--json out]
"""

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

from scipy import stats

SEEDS = range(4, 10)
PREDICTED = (0.026, 0.030)  # one-pair block model, section 3 of the report
BAND = (0.015, 0.045)  # written before any count was read
FIT_ONLY_CV = 0.0909  # reports/fit_rng_dominates_the_flatten_was_never_binding.md


def ink(so: Path, arm: str) -> int:
    return json.loads((so / arm / "ink_metric" / "metrics.json").read_text())[
        "summary"
    ]["total_fg_pixels"]


def summarise(pairs: dict[str, dict[str, int]]) -> dict:
    ln = [math.log(p["det"] / p["stock"]) for p in pairs.values()]
    n = len(ln)
    sd = st.stdev(ln)
    df = n - 1
    return {
        "pairs": pairs,
        "ln_ratio": ln,
        "mean_ln_ratio": st.mean(ln),
        "sd_ln_ratio": sd,
        "sd_ci95": [
            sd * math.sqrt(df / stats.chi2.ppf(0.975, df)),
            sd * math.sqrt(df / stats.chi2.ppf(0.025, df)),
        ],
        # undefined when every pair agrees exactly; None, not a ZeroDivisionError
        "t_mean": st.mean(ln) / (sd / math.sqrt(n)) if sd > 0 else None,
        "predicted": list(PREDICTED),
        "band": list(BAND),
        "in_band": BAND[0] <= sd <= BAND[1],
        "layout_share_of_fit_variance": (sd / FIT_ONLY_CV) ** 2,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)
    pairs = {
        f"s{n}": {
            "stock": ink(so, f"outer_curbase_s{n}"),
            "det": ink(so, f"detfit_s{n}"),
        }
        for n in SEEDS
    }
    r = summarise(pairs)
    for k, p in pairs.items():
        print(
            f"  {k}: stock {p['stock']:>10,}  det {p['det']:>10,}  det/stock {p['det'] / p['stock']:.4f}"
        )
    lo, hi = r["sd_ci95"]
    print(
        f"\n  sd ln(det/stock) {r['sd_ln_ratio']:.4f}  95% CI [{lo:.4f}, {hi:.4f}]"
        f"   predicted {PREDICTED[0]}-{PREDICTED[1]}, band {BAND[0]}-{BAND[1]}: "
        f"{'IN BAND' if r['in_band'] else 'OUT OF BAND'}"
    )
    t = "n/a" if r["t_mean"] is None else f"{r['t_mean']:.2f}"
    print(f"  mean ln ratio {r['mean_ln_ratio']:+.4f} (t = {t})")
    print(
        f"  layout share of the fit-only variance: {r['layout_share_of_fit_variance']:.1%}"
    )
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
