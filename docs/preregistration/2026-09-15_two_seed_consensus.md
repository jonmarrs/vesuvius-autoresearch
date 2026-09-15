# Pre-registration: does the model hold at k = 2, the case actually being recommended?

**Written 2026-09-15, after the k=3 result was known and before any k=2 number is computed.**
`reports/consensus_retest_confirmed.md` is the k=3 result.

## The gap this closes

The confirmed study measured **k = 3** (predicted 0.877, measured 0.875 and 0.893). The
recommendation it licenses is about **k = 2**: *"a loop already paying for two seeds should keep the
consensus rather than the winner."* villa's loop runs two seeds, not three. **So the advice rests on a
point of the model that has not been tested**, and the honest fix is to test it rather than soften the
wording.

The same independent-noise model, `r_k = 1/(1 + ratio/k)` with `ratio = 0.4204` from the measured
`r_single = 0.7040` over all 15 pairs of `s1–s6` (verified exactly, seventh amendment), gives:

| k | predicted |
|---:|---:|
| 1 | 0.7040 |
| **2** | **0.8263** |
| 3 | 0.8771 |

## Design

**Render-clean arms only.** Triplet A (`s1–s3`) rendered from `d8c5f488a`; B and C are on
`be09a8503`. To keep this free of the confound the k=3 study had to bound, **only B and C arms are
used**: `s4, s5, s6, s7, s8, s9`.

Three disjoint pair-vs-pair comparisons, each a 2-seed consensus against another 2-seed consensus:

| # | left | right |
|---|---|---|
| 1 | `s4 + s5` | `s7 + s8` |
| 2 | `s4 + s6` | `s7 + s9` |
| 3 | `s5 + s6` | `s8 + s9` |

Each comparison is disjoint *within itself* — no arm appears on both sides. **The three comparisons
are not independent of one another**: they reuse the same six arms in different groupings, so their
spread understates true sampling variability. All three are reported; the mean is a summary, not an
estimate with three degrees of freedom.

Same instrument throughout: the (z, θ) ink histogram in volume coordinates, `compare_ink_in_volume`,
identical to the k=3 study.

## Decision rule, fixed now

Applied to the **mean** of the three comparisons, with all three shown whatever they do:

| observed mean r | conclusion |
|---|---|
| 0.80 – 0.86 | **CONFIRMED.** The model holds at the k actually recommended. |
| 0.86 – 0.91 | **BETTER THAN PREDICTED.** Reported as a miss of the prediction in the favourable direction, not as a success. |
| 0.74 – 0.80 | **PARTIAL.** Averaging helps but by less than the model says; the k=2 recommendation is weakened and must be restated with this number. |
| < 0.74 | **REFUTED at k=2.** The recommendation is **withdrawn**, regardless of the k=3 result. |

Band width is ±0.03 around 0.826, matching the ±0.03 the k=3 registration used around 0.877.

**If any individual comparison falls outside the band containing the mean, that is reported too**, and
the spread is quoted alongside the mean rather than buried.

## Prediction, fixed now

**mean r = 0.826**, i.e. CONFIRMED. The model has already survived one forward test at k=3 on arms
that did not exist when it was fixed; the same model at a different k on render-clean arms should
hold. Recorded so it can be a miss.

## Validity gate

The same gate as the k=3 study: every arm's `total_fg_pixels` inside 2,398,918–3,639,084, the 95% PI
from `s1–s6`. All six arms used here already passed it (`s4` 3,019,583, `s5` 2,992,717, `s6`
3,454,937, `s7` 2,974,987, `s8` 2,881,173, `s9` 2,818,864).

## What this cannot show

**Nothing about accuracy.** It measures whether two runs agree, not whether either is right. That
limit is the same one recorded for k=3 and is not weakened by a second confirmation.
