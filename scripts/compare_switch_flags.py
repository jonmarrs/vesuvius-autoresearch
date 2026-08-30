"""Do the detector's flags survive a re-fit, or is it reading optimizer noise?

THE CONTROL THIS IMPLEMENTS. Pre-registered in
`docs/preregistration/2026-08-29_sheet_switch_detector.md` under "Added control:
seed agreement", and written BEFORE the second fit finished, so the floor could
not be chosen to suit the answer.

A sheet switch is a property of the traced geometry. A flag that appears in one
fit and vanishes in another fit of the SAME data, differing only in
`optimizer_random_seed`, is a property of the optimizer instead. If agreement is
at or below chance, the detector is reported as measuring fit noise regardless of
what any injection study says about recall.

WHY JACCARD, AND WHY A FLOOR. Raw overlap counts flatter a detector that flags a
lot: two detectors each flagging 5% of 35,000 patches share ~90 patches by pure
chance. The floor is therefore computed from the two flag counts and the shared
population, and the observed Jaccard is only meaningful against it.

Two floors are reported, deliberately:

  * an ANALYTIC floor, E|A and B| = nA*nB/N under independence;
  * a PERMUTATION floor over the shared patch ids, which needs no independence
    assumption and gives a spread rather than a point.

WHAT HIGH AGREEMENT WOULD AND WOULD NOT SHOW. It would show the flags track
geometry rather than the seed. It would NOT show they are sheet switches: a
systematic artefact of the fitting procedure reproduces across seeds just as
faithfully as a real defect.

Run:
    uv run python scripts/compare_switch_flags.py --a flags_A.json --b flags_B.json
"""

import argparse
import json

import numpy as np


def jaccard(a, b):
    a, b = set(a), set(b)
    u = len(a | b)
    return (len(a & b) / u) if u else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--permutations", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260829)
    args = ap.parse_args()

    A = json.load(open(args.a))
    B = json.load(open(args.b))
    ids_a = {r["patch"] for r in A["records"]}
    ids_b = {r["patch"] for r in B["records"]}
    shared = sorted(ids_a & ids_b)
    if not shared:
        raise SystemExit("no shared patches between the two runs")

    fa = sorted(set(A["flagged"]) & set(shared))
    fb = sorted(set(B["flagged"]) & set(shared))
    n, na, nb = len(shared), len(fa), len(fb)
    inter = len(set(fa) & set(fb))
    obs = jaccard(fa, fb)

    exp_inter = na * nb / n
    analytic = (
        exp_inter / (na + nb - exp_inter) if (na + nb - exp_inter) > 0 else float("nan")
    )

    rng = np.random.default_rng(args.seed)
    idx = np.arange(n)
    perm = []
    for _ in range(args.permutations):
        a_ = set(rng.choice(idx, na, replace=False).tolist())
        b_ = set(rng.choice(idx, nb, replace=False).tolist())
        u = len(a_ | b_)
        perm.append(len(a_ & b_) / u if u else 0.0)
    perm = np.array(perm)

    print(f"run A            {A.get('run')}   flagged {na}")
    print(f"run B            {B.get('run')}   flagged {nb}")
    print(f"shared patches   {n}")
    print(f"intersection     {inter}   (chance expectation {exp_inter:.1f})")
    print()
    print(f"observed Jaccard          {obs:.4f}")
    print(f"analytic chance floor     {analytic:.4f}")
    print(
        f"permutation floor         {perm.mean():.4f}  "
        f"(p95 {np.percentile(perm, 95):.4f}, max {perm.max():.4f})"
    )
    print()
    if obs <= np.percentile(perm, 95):
        print(
            "VERDICT: at or below the chance floor. By the pre-registered reading the"
        )
        print(
            "detector is measuring FIT NOISE, not geometry, and this ends the line of work"
        )
        print("regardless of injection recall.")
    else:
        print(
            f"VERDICT: above the chance floor by {obs - perm.mean():.4f}. The flags track"
        )
        print(
            "geometry rather than the seed. This does NOT show they are sheet switches: a"
        )
        print(
            "systematic artefact of the fitting procedure would reproduce just as well."
        )


if __name__ == "__main__":
    main()
