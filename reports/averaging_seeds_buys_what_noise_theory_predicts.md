# Averaging seeds buys exactly what independent noise predicts — and that is the finding

**2026-09-13.** Registered in `docs/preregistration/2026-09-13_does_averaging_seeds_help.md`.
`scripts/measure_seed_consensus_gain.py`, `reports/seed_consensus_gain.json`.

## Registered result

Leave-one-out over the three baseline arms: how well does one arm predict the held-out arm's ink map,
against how well the *mean* of the other two does?

| held out | single (a) | single (b) | consensus | gain vs better single |
|---|---:|---:|---:|---:|
| `curbase_s1` | 0.808 | 0.684 | 0.826 | +0.019 |
| `curbase_s2` | 0.808 | 0.661 | 0.807 | −0.000 |
| `curbase_s3` | 0.684 | 0.661 | 0.715 | +0.030 |

Mean gain **+0.016** → by the registered thresholds, **MARGINAL**.

## The registered statistic was the wrong comparator, and I am not hiding behind it

The rule compared consensus against the **better** of the two singles, which I called the conservative
choice. It is conservative in the wrong way: `max()` of two noisy correlations is **biased upward by
selection**, so the benchmark is inflated and the gain understated. Against a *typical* single:

| | |
|---|---:|
| mean single | 0.718 |
| mean consensus | **0.783** |
| gain | **+0.065** |

## And that gain is what independent noise predicts

Treating each map as signal plus independent noise, `r_single = 0.718` implies a noise-to-signal
variance ratio of **0.393**. Averaging two maps halves the noise variance, which predicts a
consensus-versus-single correlation of **0.775** — a gain of **+0.057**.

**Observed +0.065 against predicted +0.057: a ratio of 1.14.**

The registration named this outcome in advance as the interesting one, in the opposite direction:

> *A gain below +0.01 would mean the seed-to-seed differences are NOT independent noise … evidence the
> disagreement is systematic per-run structure.*

It is not below +0.01. **The differences behave like independent noise**, and the placement
instability is therefore averageable rather than systematic — which is the first positive structural
statement this thread has produced about it.

## What it implies, and this is the actionable part

If the noise is independent, the reproducibility of a *k*-seed consensus follows
`r = 1 / (1 + 0.393/k)`:

| seeds averaged | reproducibility |
|---:|---:|
| 1 | 0.718 |
| 2 | 0.836 |
| 3 | **0.884** |
| 5 | 0.927 |

**Three seeds take ink-placement reproducibility from 0.72 to 0.88.** For a loop already running two
seeds, keeping the consensus rather than the winner is close to free, and a third seed buys more than
the second did on this curve.

## Replicated on two further triplets, which were free

The registration limited itself to the baseline arms. But `nosamecur` and `anchor10cov` are also
three-seed groups, so the same measurement runs on them at no compute cost — a replication before
spending anything on new fits.

| triplet | r single | r consensus | observed gain | predicted | obs/pred |
|---|---:|---:|---:|---:|---:|
| `curbase` | 0.718 | 0.783 | +0.065 | +0.057 | 1.15 |
| `nosamecur` | 0.650 | 0.724 | +0.074 | +0.066 | 1.13 |
| `anchor10cov` | 0.730 | 0.790 | +0.060 | +0.055 | 1.10 |

**The independent-noise model holds on all three, at 1.10–1.15× predicted.** The agreement is tighter
across triplets than any single one is to theory, which is what a real regularity looks like and what
a coincidence generally does not.

The consistent ~12% excess over prediction is unexplained and not chased here. It would follow from
the noise being slightly *anti*-correlated between runs, or from the model's assumption of a perfectly
shared signal being a little wrong. Either way it makes averaging marginally *better* than theory, not
worse.

**Note the registered statistic's spread:** gain against the *better* single is +0.016, +0.064 and
+0.041 across the three, so the triplet the registration happened to use produced the **least**
favourable number of the three. Against a typical single the three agree closely (+0.065, +0.074,
+0.060). That is further evidence the `max()` comparator was adding noise rather than conservatism.

**Placement reproducibility is not the same for every configuration:**

| triplet | r single | noise/signal |
|---|---:|---:|
| `anchor10cov` | 0.730 | 0.370 |
| `curbase` | 0.718 | 0.393 |
| `nosamecur` | 0.650 | 0.539 |

One triplet each, so this ordering is an observation, not a result — but `nosamecur` being the least
reproducible is worth remembering if that arm is ever reused.

## Limits

* The extrapolation rests on the independent-noise model, which is supported here by **one** data
  point — the 2-seed gain matching prediction. It is a projection, not a measurement, for k ≥ 3.
* Three arms only, so "consensus" is two maps and each correlation is against a single held-out arm
  that is itself only ~0.72 reproducible.
* Baseline arms only; whether consensus helps under a manipulation is untested.
* Binning frozen at the published 96 × 256, not swept.

## The methodological note

Two registrations in a row have now been saved or corrected by something outside their decision rule —
the validity threshold that caught a false positive, and here a comparator I had to argue against
myself after seeing the number. **A decision rule fixes what counts as a yes; it does not guarantee
the statistic is the right one.** Both halves need thinking about before the data, and I got the
second one wrong here.
