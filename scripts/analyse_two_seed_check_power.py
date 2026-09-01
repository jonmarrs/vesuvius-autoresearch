"""How well does the two-seed robustness check separate a real gain from noise?

`spiral-fitting/autoresearch.md` prescribes it:

    "Prefer changes that are robust across seeds/runs, not ones that only help
     for one specific seed. Since you run two at a time, a cheap robustness
     check is to run the same change under two seeds concurrently and see if
     the ink gain survives."

That is the right instinct, and `reports/seed_spread_four_fits.md` measured the
noise it has to beat: CV 0.1086 on `total_fg_pixels` across four fits differing
only in seed, worst pair 25.3%. Nobody has asked what the check's error rates
ARE at that noise level. This asks.

METHOD, FIXED BEFORE COMPUTING ANYTHING:

  Two estimates, reported together, because each is weak where the other is not.

  1. EXACT, assumption-free, tiny n. Take the four measured null values. Split
     them into all 3 distinct pairs-of-pairs. Under the null both arms are the
     same distribution, so each split is a valid "baseline pair vs change pair"
     draw with a TRUE effect of zero. Count how often the "change" pair looks
     better. n=3 splits is far too few to trust alone, which is why 2 exists.

  2. PARAMETRIC, stated assumption. Model the null as lognormal-ish via a normal
     on the log of the four values, with the measured spread. Simulate 200,000
     experiments where the change has a KNOWN true effect, and report how often
     the two-seed check calls it. Assumption: the seed distribution is
     approximately normal in log space. n=4 cannot test that assumption, and
     that limit is stated in the output rather than buried.

  Two decision rules are scored, both of which a reader of autoresearch.md could
  reasonably adopt:
     RULE A "survives both seeds": accept if BOTH change runs beat BOTH baseline runs.
     RULE B "mean improves":       accept if the mean of 2 beats the mean of 2.

  Reported for each: false-positive rate at true effect 0, and power at true
  effects of +5%, +10%, +20%, +30%.

No statistic is selected after seeing output; all of the above is fixed here.
"""

import itertools
import statistics

import numpy as np

# The four measured values, reports/seed_spread_four_fits.md. Identical config,
# seed the only difference, all four inside the pre-registered quality band.
NULL_VALUES = [240088.0, 194634.0, 221576.0, 250936.0]
EFFECTS = [0.0, 0.05, 0.10, 0.20, 0.30]
N_SIM = 200_000
SEED = 20260901


def exact_pairs_of_pairs(vals):
    """All distinct ways to split 4 values into (baseline pair, change pair)."""
    out = []
    for combo in itertools.combinations(range(4), 2):
        rest = tuple(i for i in range(4) if i not in combo)
        if combo < rest:  # each partition once
            out.append(([vals[i] for i in rest], [vals[i] for i in combo]))
    return out


def rule_a(base, chg):
    """Survives both seeds: every change run beats every baseline run."""
    return min(chg) > max(base)


def rule_b(base, chg):
    """Mean improves."""
    return statistics.fmean(chg) > statistics.fmean(base)


def main():
    v = np.array(NULL_VALUES)
    logv = np.log(v)
    mu, sigma = logv.mean(), logv.std(ddof=1)
    print("four measured null values:", ", ".join(f"{x:,.0f}" for x in NULL_VALUES))
    print(f"CV {v.std(ddof=1) / v.mean():.4f}   log-sd {sigma:.4f}\n")

    print("1. EXACT over the 3 distinct pairs-of-pairs (true effect = 0):")
    splits = exact_pairs_of_pairs(NULL_VALUES)
    for name, rule in (("A survives both", rule_a), ("B mean improves", rule_b)):
        hits = sum(rule(b, c) or rule(c, b) for b, c in splits)
        print(
            f"   rule {name:<16} {hits}/{len(splits) * 2} orderings call a null change a win"
        )
    print(
        "   (3 splits is far too few to trust; it exists to bound the parametric model)\n"
    )

    rng = np.random.default_rng(SEED)
    print(f"2. PARAMETRIC, {N_SIM:,} simulated experiments, normal in log space:")
    print(f"   {'true effect':>12}{'rule A accepts':>16}{'rule B accepts':>16}")
    for eff in EFFECTS:
        base = rng.normal(mu, sigma, (N_SIM, 2))
        chg = rng.normal(mu + np.log1p(eff), sigma, (N_SIM, 2))
        a = (chg.min(1) > base.max(1)).mean()
        b = (chg.mean(1) > base.mean(1)).mean()
        tag = "  <- FALSE POSITIVE rate" if eff == 0 else ""
        print(f"   {eff:>11.0%}{a:>15.1%}{b:>16.1%}{tag}")

    print("\n3. HOW MANY SEEDS would the check need? (false-positive rate at effect 0)")
    print(f"   {'seeds/arm':>10}{'rule A':>10}{'rule B':>10}{'cost (fits)':>13}")
    for k in (2, 3, 4, 5, 6, 8):
        base = rng.normal(mu, sigma, (N_SIM, k))
        chg = rng.normal(mu, sigma, (N_SIM, k))
        a = (chg.min(1) > base.max(1)).mean()
        b = (chg.mean(1) > base.mean(1)).mean()
        print(f"   {k:>10}{a:>9.1%}{b:>10.1%}{2 * k:>13}")
    print("   rule B is a coin flip at EVERY k: comparing two means of equal")
    print("   distributions is 50/50 however many seeds you average.")

    print("\nLimits: four fits, one dataset, one ROI. The parametric arm assumes")
    print("approximate log-normality, which n=4 cannot test. Both arms assume the")
    print("change alters only the mean, not the seed spread itself.")


if __name__ == "__main__":
    main()
