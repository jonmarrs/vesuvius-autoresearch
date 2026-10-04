"""docs/preregistration/2026-10-04_soft_count.md -- would an unthresholded ink count (S = sum of probability) make
villa's loop decisions less noisy than total_fg_pixels (H), without losing sensitivity?

Reads <study>/<arm>/sums.json (written by soft_count_sums.py) and each arm's published metrics.json.

Usage: .venv/bin/python scripts/soft_count_study.py [--study DIR] [--out reports/soft_count_study.json]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
PINNED = {
    "baselines": ["baseline01", "seed02", "seed03", "seed04", "seed05", "seed06"],
    "gap133": ["gap133", "gap133s2", "gap133s3", "gap133s4", "gap133s5", "gap133s6"],
}
CURRENT = {
    "curbase_d8c5f488a": ["curbase_s1", "curbase_s2", "curbase_s3"],
    "curbase_be09a8503": [f"curbase_s{i}" for i in range(4, 10)],
    "nosamecur": [f"nosamecur_s{i}" for i in range(1, 7)],
}
OFFSETS = {-4: "flat_study_in", -2: "offset_m2", 0: "flat_study_zero", 1: "offset_p1",
           2: "offset_p2", 3: "offset_p3", 4: "flat_study_out"}  # fmt: skip
PROBE = "flat_study_probe"
PUBLISHED_SD = {"pinned": 0.0423, "current": 0.0608}
V1_TOL, V2_TOL, V3_TOL = 0.001, 0.001, 0.002
N_BOOT, SEED = 10_000, 20261005


def arm_dir(arm: str) -> str:
    return arm if arm in OFFSETS.values() or arm == PROBE else f"outer_{arm}"


def load_arm(study: Path, arm: str) -> dict:
    s = json.loads((study / arm_dir(arm) / "sums.json").read_text())
    pub = json.loads((SO / arm_dir(arm) / "ink_metric/metrics.json").read_text())[
        "summary"
    ]
    h_pub = int(pub["total_fg_pixels"])
    return {
        "H": s["H"],
        "S": s["S"],
        "H_published": h_pub,
        "v1_rel": s["H"] / h_pub - 1,
    }


def pooled_sd(groups: list[list[float]]) -> tuple[float, int]:
    """Pooled within-group SD of ln(values)."""
    ss, df = 0.0, 0
    for g in groups:
        if len(g) < 2:
            continue
        x = np.log(np.asarray(g, dtype=float))
        ss += float(((x - x.mean()) ** 2).sum())
        df += len(g) - 1
    if df == 0:
        raise ValueError("no group with two or more fits")
    return math.sqrt(ss / df), df


def ratio_with_ci(
    h: list[list[float]], s: list[list[float]], rng: np.random.Generator
) -> dict:
    """R = sd(ln S) / sd(ln H), bootstrap resampling fits within groups, paired across the two metrics."""
    sd_h, df = pooled_sd(h)
    sd_s, _ = pooled_sd(s)
    boot = []
    for _ in range(N_BOOT):
        hh, sss = [], []
        for gh, gs in zip(h, s, strict=True):
            idx = rng.integers(0, len(gh), len(gh))
            hh.append([gh[i] for i in idx])
            sss.append([gs[i] for i in idx])
        bh, bs = pooled_sd(hh)[0], pooled_sd(sss)[0]
        boot.append(bs / bh if bh > 0 else np.nan)
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])
    return {
        "sd_H": sd_h,
        "sd_S": sd_s,
        "df": df,
        "R": sd_s / sd_h,
        "ci": [float(lo), float(hi)],
    }


def classify(lo: float, hi: float, better: str, worse: str) -> str:
    if hi < 1:
        return better
    if lo > 1:
        return worse
    return "no detectable difference"


def seed_tier(study: Path, groups: dict, tier: str, rng: np.random.Generator) -> dict:
    vals = {g: {a: load_arm(study, a) for a in arms} for g, arms in groups.items()}
    failed = [
        a for g in vals.values() for a, v in g.items() if abs(v["v1_rel"]) > V1_TOL
    ]
    h = [[v["H"] for a, v in g.items() if a not in failed] for g in vals.values()]
    s = [[v["S"] for a, v in g.items() if a not in failed] for g in vals.values()]
    r = ratio_with_ci(h, s, rng)
    void = len(failed) > 2
    v3 = abs(r["sd_H"] - PUBLISHED_SD[tier]) <= V3_TOL
    return {"arms": vals, "v1_failed": failed, "void": void, "v3_sd_H_matches_published": v3, **r,
            "verdict": "VOID" if void else classify(r["ci"][0], r["ci"][1], "S less noisy", "S noisier")}  # fmt: skip


def offsets(study: Path, R: dict) -> dict:
    vals = {k: load_arm(study, a) for k, a in OFFSETS.items()}
    probe = load_arm(study, PROBE)
    failed = [OFFSETS[k] for k, v in vals.items() if abs(v["v1_rel"]) > V1_TOL]
    z = vals[0]
    v2 = {m: math.log(probe[m]) - math.log(z[m]) for m in ("H", "S")}
    v2_ok = all(abs(x) <= V2_TOL for x in v2.values())
    per_k = {}
    for k, v in vals.items():
        if k == 0:
            continue
        dh, ds = (
            math.log(v["H"]) - math.log(z["H"]),
            math.log(v["S"]) - math.log(z["S"]),
        )
        per_k[k] = {"dH": dh, "dS": ds, "a": ds / dh, "sign_agrees": (dh > 0) == (ds > 0),
                    "z_H": abs(dh) / R["sd_H"], "z_S": abs(ds) / R["sd_S"]}  # fmt: skip
    a_med = float(np.median([p["a"] for p in per_k.values()]))
    D = a_med / R["R"]
    ci = sorted([a_med / R["ci"][1], a_med / R["ci"][0]])
    void = bool(failed) or not v2_ok
    return {"arms": {str(k): v for k, v in vals.items()}, "probe": probe, "v1_failed": failed, "v2": v2,
            "v2_ok": v2_ok, "per_offset": {str(k): p for k, p in per_k.items()}, "a_median": a_med,
            "D": D, "D_ci": ci, "void": void, "verdict": "VOID" if void else d_verdict(a_med, ci)}  # fmt: skip


def d_verdict(a_med: float, ci: list[float]) -> str:
    """Higher D is better. A soft count that moves against the hard count (a <= 0) discriminates worse."""
    if a_med <= 0 or ci[1] < 1:
        return "S discriminates worse"
    if ci[0] > 1:
        return "S discriminates better"
    return "no detectable difference"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, default=SO / "softcount_study")
    ap.add_argument("--out", type=Path, default=Path("reports/soft_count_study.json"))
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    pinned = seed_tier(args.study, PINNED, "pinned", rng)
    q2 = offsets(args.study, pinned)
    current = seed_tier(args.study, CURRENT, "current", rng)
    rec = (
        pinned["verdict"] == "S less noisy"
        and q2["verdict"] not in ("S discriminates worse", "VOID")
        and (
            current["verdict"] == "S less noisy"
            or (not current["void"] and current["R"] < 1)
        )
    )
    res = {"pinned_q1": pinned, "q2": q2, "current_q1": current, "recommend_S": rec,
           "predictions": {"P1_pinned_less_noisy": pinned["verdict"] == "S less noisy",
                           "P2_no_detectable_difference": q2["verdict"] == "no detectable difference",
                           "P3_current_less_noisy": current["verdict"] == "S less noisy"}}  # fmt: skip
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    for name, t in (("pinned", pinned), ("current", current)):
        print(f"Q1 {name}: sd_H {t['sd_H']:.4f} sd_S {t['sd_S']:.4f} df {t['df']}  R {t['R']:.3f} "
              f"[{t['ci'][0]:.3f}, {t['ci'][1]:.3f}]  V1 failed {t['v1_failed']}  V3 {t['v3_sd_H_matches_published']}"
              f"  -> {t['verdict']}")  # fmt: skip
    for k, p in q2["per_offset"].items():
        print(f"  offset {int(k):+d}: dH {p['dH']:+.4f} dS {p['dS']:+.4f} a {p['a']:+.3f} z_H {p['z_H']:.2f} z_S {p['z_S']:.2f}")  # fmt: skip
    print(f"Q2: V2 {q2['v2']} ok={q2['v2_ok']}  a_median {q2['a_median']:+.3f}  D {q2['D']:.3f} "
          f"[{q2['D_ci'][0]:.3f}, {q2['D_ci'][1]:.3f}]  -> {q2['verdict']}")  # fmt: skip
    print("recommend S:", rec, " predictions:", res["predictions"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
