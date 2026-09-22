# Fit RNG dominates: with the flatten made deterministic, the seed CV is 0.09 [0.06, 0.22]

**2026-09-22.** Registered in `docs/preregistration/2026-09-21_fit_only_noise_floor.md`, decided by
`scripts/analyse_fit_only_floor.py`, both committed before any arm scored.
`reports/fit_only_floor.json`.

## What was measured

Six fits — `curbase_s4..s9`, identical config, seeds 4–9, one villa tree `be09a8503` — each
re-flattened under `FLATTEN_DETERMINISTIC=1`, rendered on the pinned image, and scored. Work dirs
`detfit_s4..s9`. **No new fits.** The flatten's contribution to run-to-run noise is exactly zero
(byte-identical surfaces, `reports/the_flatten_is_reproducible_when_asked.md`), so the within-group
spread that remains is fit RNG plus the ~0.003% scorer.

Every arm's guard confirmed the shim active in the flatten subprocess before proceeding; the first
launch ran at stock speed under a deterministic label and was killed before it scored.

## The result

| seed | stock | deterministic | shift |
|---|---:|---:|---:|
| s4 | 3,019,583 | 3,164,499 | +4.80% |
| s5 | 2,992,717 | 2,963,832 | −0.97% |
| s6 | 3,454,937 | 3,583,420 | +3.72% |
| s7 | 2,974,987 | 3,018,973 | +1.48% |
| s8 | 2,881,173 | 2,837,373 | −1.52% |
| s9 | 2,818,864 | 2,848,719 | +1.06% |

| | CV | 95% CI (df=5) |
|---|---:|---|
| **deterministic flatten** | **0.0909** | **[0.0568, 0.2230]** |
| stock flatten, same six fits | 0.0742 | [0.0463, 0.1820] |

**The interval is the finding.** A CV at df=5 spans a factor of 3.9, and this project has quoted the
point estimate alone three times and been wrong three times.

## Band: FIT RNG DOMINATES. Prediction 1: MISS

I predicted the fit-only CV would land in **[0.030, 0.055]**. It landed at **0.0909** — above the
registered band, and above the *stock* CV it was supposed to be a reduction of. **Recorded as a
miss**, the fourth missed magnitude in a week.

**The flatten's 3% was never the binding constraint on fit comparisons.** Making it deterministic
does not detectably tighten the seed spread; the design MDE at 3v3 is **20.8%** from this CV, against
17.0% on stock — no improvement, within noise.

## The number that needed a control before being read

**The deterministic CV is *higher* than the stock CV.** If the flatten only added independent noise,
removing it could not increase the spread — an additive model predicts a fit-only CV between 0.055
and 0.074 depending on where in its interval the flatten σ sits, and 0.0909 is outside all of it.

Two explanations, and only one can be claimed:

* **Sampling.** Two CVs at df=5 from the same six fits: variance ratio 1.50, **F(5,5) two-sided
  p = 0.666**. They are indistinguishable. Two draws from one distribution.
* Anti-correlation between flatten and fit variation on this set. *Consistent with* the numbers;
  **not claimed**, because sampling is sufficient and cannot be excluded.

So the honest statement is not "deterministic mode is noisier". It is: **removing the flatten did not
reduce the spread detectably at n=6**, which is what "fit RNG dominates" means.

## Predictions 2 and 3

**2. `curbase_s6` remains the top scorer — MET**, resolved at arm three. Deterministic `s6` leads the
next-highest by +13.2% against a 14.4% stock lead; the gap survived re-flattening. `s6` is a
genuine fit outlier, and it carries most of *both* spreads (without it: det 0.0454, stock 0.0287).
It stays in: a genuine outlier is part of the fit distribution, and excluding it would quote a floor
too low — the error this line of work exists to stop.

**3. Shifts carry no particular sign** — mean +1.43%, signs 4+/2−. Consistent; six points do not
test it.

## What this changes

**Nothing about `FLATTEN_DETERMINISTIC=1` for surface-manipulation studies**, where it took the floor
from 3.04% to 0.0014% and the ±4 vx displacement result stands on it.

**For fit comparisons, the honest position is now measured rather than inferred:** at 3v3 the floor is
~20%, it is fit RNG, and there is no cheap lever for it — not the flatten, not more render care. A
fit comparison that needs to see 5% needs roughly **n=13 per arm** at this CV, which is the number
villa's loop and this project's studies have never had. Every null in
`reports/no_lever_has_improved_reading.md` was already quoted against a 10–12% MDE; this says even
that was optimistic for the current tier.

## What it cannot do — computed before the number existed

No published null becomes decisive: the largest observed null effect (5.49%) sits below the most
favourable MDE (5.7%) in every band, and this result landed in the least favourable. This bears on
how many seeds **future** studies need. It reopens nothing.

## Limits

Six seeds, one config, one tree; a CV at df=5, and the interval [0.0568, 0.2230] is what these data
support. It does not partition the residual beyond "not the flatten" — fit RNG, or fit RNG plus
something undecomposed, are both consistent. Nothing here about the pinned tier. Wall time per arm
ran 80–160 min, the spread entirely in the S3-fetch bands.
