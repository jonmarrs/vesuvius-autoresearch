# The noise floor every study here quotes is wrong in both directions

**2026-09-12.** Exploratory, prompted by noticing that yesterday's verdict quoted a bound derived
from a constant measured on a different tree. `scripts/measure_noise_floor.py`,
`reports/noise_floor_by_tier.json`.

Every analysis script in this repo hardcodes `OUTER_CV = 0.0421` and converts it into a statement
about what a null excludes. That constant is real and this script reproduces it exactly from its own
four fits — but it carries **df = 3**, and it has since been used to describe the power of studies on
a tree it was never measured on.

## Measured from the corpus, per tier

Pooled **within-arm** relative deviations: seeds inside an arm differ only by RNG, so their spread is
noise, while between-arm differences are the manipulations and are never pooled.

| tier | arms | fits | pooled CV | df | 95% CI | MDE at 3v3 |
|---|---:|---:|---:|---:|---|---:|
| pinned `6847063f` | 6 | 24 | **0.0514** | 18 | [0.0388, 0.0760] | **11.8%** |
| current villa | 2 | 6 | **0.0125** | 4 | [0.0075, 0.0360] | **2.9%** |

## Correction 1, and it goes against us

**The hardcoded 0.0421 is optimistic.** With 18 df instead of 3, pinned-tier seed noise is **0.0514**.
Every "no effect larger than about 10%" we published on that tree should have read **about 12%**.

The nulls stand — this widens what they failed to exclude, it does not move any verdict — but they
exclude less than they claimed, and that is the direction an error should never be left uncorrected.

## Correction 2, in our favour, and it is post-hoc

Current-code seed noise is **4.1× tighter** (F(18,4) = 16.79, p = 0.0143). Both current arms agree
independently — 0.0124 and 0.0127 — which is what makes it credible at n=3 per arm; it is not one
lucky arm. The larger canvas cannot explain it: strips are 14% bigger, worth only a 1.07× reduction
under the averaging argument, not 4.1×.

**This was noticed in the data, not registered.** It is a refinement, never a result, and the tier
comparison is reported with that label in the script's own output.

## What that does to yesterday's null — it is much stronger than published

`reports/decoupling_does_not_cleanly_reproduce.md` reported the same-winding ablation as "no effect
larger than 9.6%", using the pinned-tier constant. The registered design-stage figure stays on the
record, but the honest post-hoc statement is a confidence interval on what was actually observed:

> ink effect **+0.28%, 95% CI [−2.56%, +3.13%]** (Welch, df = 4.0)

**The data exclude any ink effect beyond roughly ±3%, not ±10%.** The verdict does not change — the
decoupling still fails to extend — but the null is three times more informative than stated.

## A trap worth recording: do not normalise by strip area

Dividing ink by strip size is the natural instinct and it **costs power**:

| tier | CV(`total_fg_pixels`) | CV(`overall_fg_fraction`) |
|---|---:|---:|
| pinned | 0.0514 | 0.0499 (no gain, F p = 0.90) |
| current | **0.0125** | **0.0320** (2.6× WORSE, F p = 0.097) |

On current code `total_fg_pixels` is quieter than the strip it sits on (0.0125 vs strip 0.0242), so
the canvas fluctuates in regions holding no ink. Dividing by it injects that noise into the ratio.
**Keep the raw count.**

## Consequences

1. Future studies on current code need far fewer fits: 3v3 now sees **2.9%**, where the pinned tier
   needed six seeds an arm to approach 8%.
2. The pinned-tier MDE in `analyse_gap_ink_arm.py`, `analyse_patch_bootstrap.py`,
   `analyse_stripmatch.py` and `analyse_same_winding.py` is **understated by ~23%**. Those scripts
   keep their registered constant so they still reproduce what was published; the correction lives
   here and in the reports.
3. Registering a new current-code study against 0.0421 would over-provision seeds by ~16×.
