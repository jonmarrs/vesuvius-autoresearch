# Pre-registration: does the detector's confidence predict which ink reproduces?

**Written 2026-09-13, before any probability map has been produced.** Queued behind the consensus
study; nothing here runs until that chain finishes, because scoring competes with a render for the
box.

## The question

Roughly 28% of a run's recovered ink does not reproduce under a different RNG seed
(`reports/ink_placement_in_volume.md`: placement agrees at r ≈ 0.70, and the differences behave like
independent noise). **If the detector's own confidence separates the reproducible ink from the rest,
then raising the threshold is a cheaper route to stability than averaging seeds.**

That matters because the alternative already has a price: a 3-seed consensus needs 3× the compute,
while a threshold change costs nothing.

## Why this is not already answerable

The scorer computes a per-pixel probability, thresholds it, and **discards the gradation** — the saved
masks contain exactly two values, 0 and 255. `repro/spiral_render/keep_probabilities.patch` preserves
it behind `INK_METRIC_KEEP_PROB=1`, gated so the default path stays byte-identical to upstream.
Verified 2026-09-13 to still apply cleanly to villa `be09a8503`.

**The existing arms must therefore be re-scored**, not re-rendered: ~16 minutes per arm, GPU, from
renders already on disk. Three baseline arms ≈ 50 minutes.

## What is measured

Re-score `curbase_s1/s2/s3` with probabilities kept. For each (z, θ) bin in the volume frame already
used, and for each arm, bin the ink by **how many of the three arms find ink there** (1, 2 or 3), then
compare the mean detector probability of each group.

**Statistic: mean probability of ink in unanimous bins minus mean probability of ink in bins only one
arm found.** Null by shuffling the agreement labels across bins, 1,000 times.

## Decision rule, fixed now

| outcome | conclusion |
|---|---|
| difference **> 0.05** probability, p < 0.05 | **Confidence predicts reproducibility.** A higher threshold would preferentially discard the irreproducible ink, and the trade against lost recall is then worth measuring. |
| **0 to 0.05**, or not significant | **It does not.** The irreproducible ink is not distinguishable by confidence, so thresholding cannot separate it and averaging remains the only lever. |
| **negative**, p < 0.05 | Reproducible ink is *less* confident, which no account predicts; reported as a surprise. |

## Validity gate

* **Bin-size dependence must be reported, not chosen.** The agreement fractions move from 89.7% to
  43.2% across binnings (`ink_placement_in_volume.md`), so the probability difference is computed at
  **three** binnings — 48×128, 96×256, 192×512 — and **the conclusion must hold at all three** or it
  is reported as bin-dependent and not as a finding. This is the direct lesson from the consensus
  fraction I nearly published.
* Re-scored `total_fg_pixels` must match the existing value for each arm to within 0.1%. The patch is
  meant to be inert on the default path; if the numbers move, it is not, and the result is void.

## What it cannot show

* Confidence predicting reproducibility would not mean the reproducible ink is *correct*. There is no
  ground truth on this ROI, and this compares runs to each other.
* Three arms, one configuration.

## Prediction

**None registered.**
