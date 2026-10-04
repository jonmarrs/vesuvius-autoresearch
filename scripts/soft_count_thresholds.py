"""docs/preregistration/2026-10-04_soft_count.md, Amendment 1 -- SECONDARY, descriptive: hard counts at lower
thresholds (villa's scorer already takes --fg-threshold), with the same R and D statistics as the soft count.

Per arm, counts float16 probability >= t for each t in THRESHOLDS and caches <study>/<arm>/thresholds.json. Then
R(t) = sd(ln H_t)/sd(ln H) and D(t) = median_k[dH_t(k)/dH(k)]/R(t), as in soft_count_study.py.

Usage: .venv/bin/python scripts/soft_count_thresholds.py [--study DIR] [--out reports/soft_count_thresholds.json]
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import soft_count_study as scs  # noqa: E402

THRESHOLDS = (0.1, 0.2, 0.3, 0.4, 0.5)
ROWS = 256


def counts(prob: np.ndarray) -> dict[str, int]:
    out = dict.fromkeys((f"{t:.1f}" for t in THRESHOLDS), 0)
    for i in range(0, prob.shape[0], ROWS):
        b = np.asarray(prob[i : i + ROWS])
        for t in THRESHOLDS:
            out[f"{t:.1f}"] += int((b >= np.float16(t)).sum())
    return out


def arm_counts(study: Path, arm: str) -> dict[str, int]:
    d = study / scs.arm_dir(arm)
    cache = d / "thresholds.json"
    if cache.exists():
        return json.loads(cache.read_text())
    prob = json.loads((d / "sums.json").read_text())["prob"]
    assert glob.glob(prob), prob
    c = counts(np.load(prob, mmap_mode="r"))
    cache.write_text(json.dumps(c, indent=2) + "\n")
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, default=scs.SO / "softcount_study")
    ap.add_argument(
        "--out", type=Path, default=Path("reports/soft_count_thresholds.json")
    )
    args = ap.parse_args()
    res: dict = {"registered": "secondary, descriptive (Amendment 1)", "tiers": {}}
    for tier, groups in (("pinned", scs.PINNED), ("current", scs.CURRENT)):
        arms = [a for g in groups.values() for a in g]
        H = {a: scs.load_arm(args.study, a)["H"] for a in arms}
        C = {a: arm_counts(args.study, a) for a in arms}
        res["tiers"][tier] = {}
        for t in THRESHOLDS:
            key = f"{t:.1f}"
            h = [[H[a] for a in g] for g in groups.values()]
            ht = [[C[a][key] for a in g] for g in groups.values()]
            r = scs.ratio_with_ci(h, ht, np.random.default_rng(scs.SEED))
            res["tiers"][tier][key] = r
            print(
                f"{tier:7s} t={key}: sd_H {r['sd_H']:.4f} sd_Ht {r['sd_S']:.4f}  R {r['R']:.3f} [{r['ci'][0]:.3f}, {r['ci'][1]:.3f}]"
            )
    H0 = {k: scs.load_arm(args.study, a)["H"] for k, a in scs.OFFSETS.items()}
    C0 = {k: arm_counts(args.study, a) for k, a in scs.OFFSETS.items()}
    res["offsets"] = {}
    for t in THRESHOLDS:
        key = f"{t:.1f}"
        a = [
            (np.log(C0[k][key]) - np.log(C0[0][key])) / (np.log(H0[k]) - np.log(H0[0]))
            for k in H0
            if k != 0
        ]
        a_med = float(np.median(a))
        R = res["tiers"]["pinned"][key]
        ci = sorted([a_med / R["ci"][1], a_med / R["ci"][0]])
        res["offsets"][key] = {"a": [float(x) for x in a], "a_median": a_med, "D": a_med / R["R"], "D_ci": ci,
                               "verdict": scs.d_verdict(a_med, ci)}  # fmt: skip
        print(
            f"offsets t={key}: a_median {a_med:+.3f}  D {a_med / R['R']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]"
        )
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
