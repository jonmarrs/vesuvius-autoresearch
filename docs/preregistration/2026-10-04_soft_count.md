# Pre-registration: would an unthresholded ink count make villa's loop decisions less noisy?

**Written 2026-10-04, before any soft-count value was computed for a pinned-tier or offset arm.** Scripts
committed with this file: `scripts/soft_count_sums.py`, `scripts/soft_count_study.py`,
`repro/spiral_render/run_soft_count_chain.sh`.

## Question

villa's objective `total_fg_pixels` counts pixels where the scorer's ensemble probability is ≥ 0.5.
Finding 78 found that count marks about 2% of villa's annotated ink. The probability before the threshold
tracked labelled density better (ρ +0.47 vs +0.17 at 128 px, descriptive).

villa's loop decides keep/discard on a count with seed noise of 4–6%. The natural alternative is the
**soft count** S = Σ probability over the strip, against the **hard count** H = `total_fg_pixels`.
A better objective for the loop must be both:
1. **less noisy** across RNG seeds, and
2. **no less sensitive** to a change known to cost ink, per unit of its own noise.

A metric that is stabler only because it responds less is no better.

## What is already known (and was looked at before writing this)

* Published H, pooled within-group SD of ln H:
  * pinned tier (baselines ×6, gap133 ×6): **0.0423**, df 10;
  * current tier (curbase_d8c5f488a ×3, curbase_be09a8503 ×6, nosamecur ×6): **0.0608**, df 12.
* Published H on one pinned-tier flattened surface, displaced radially with the flatten held fixed
  (`reports/displacing_the_surface_costs_ink_in_both_directions.md`): −4 vx −19.77%, −2 vx −8.9%,
  +1 −2.8%, +2 −2.2%, +3 −3.3%, +4 −4.48%.
  * A byte-identical re-render (`flat_study_probe`) differs from zero by −0.006%.
* One structural property of one current-tier run, `outer_curbase_s1`: S = 5.43M against H = 2.90M.
  * 61% of S lies below the threshold;
  * only 4.9% of pixels exceed probability 0.01, so S is not diffuse background.
  * **No soft-count spread between seeds, and no soft-count offset response, has been computed.**

## Data

The stored strips are re-scored with villa's scorer, the keep-probabilities patch and serial folds
(`spiral_out/gt_interp/scorer_tree`). Its only difference from the arms' own scorer is the opt-in block
that saves probabilities, verified by diff. Outputs go to `spiral_out/softcount_study/<arm>/`; **published
results are never touched.**

* **Pinned seeds (primary):**
  * baselines: `outer_baseline01`, `outer_seed02`…`06`;
  * gap133: `outer_gap133`, `outer_gap133s2`…`s6`.
* **Offset sweep (primary, pinned surface):** `flat_study_in` (−4), `offset_m2` (−2), `flat_study_zero`
  (0), `offset_p1` (+1), `offset_p2` (+2), `offset_p3` (+3), `flat_study_out` (+4), and `flat_study_probe`
  (the floor).
* **Current seeds (secondary):** curbase_s1–s3 (probability maps from 09-14, the same patched scorer, are
  reused), curbase_s4–s9 and nosamecur_s1–s6, grouped as in `scripts/measure_noise_floor.py`.

## Statistics

* **Per arm:**
  * H = `summary.total_fg_pixels` from the re-score;
  * S = Σ of the saved float16 probability map, accumulated in float64.
* **Seed noise:** σ_M = pooled within-group SD of ln M.
  * R = σ_S / σ_H.
  * 95% CI: 10,000 bootstrap resamples (seed 20261005), resampling fits within each group, the same fits for
    both metrics.
* **Sensitivity:**
  * Δ_M(k) = ln M(k) − ln M(0) at each offset k ∈ {−4, −2, +1, +2, +3, +4}.
  * a(k) = Δ_S(k) / Δ_H(k), **signed**: a soft count that rises where the hard count falls counts against it.
* **Discrimination per unit noise:** D = median_k a(k) / R, with the pinned R.
  * D > 1 means S separates the offset arms from zero by more of its own seed noise than H does.
  * The CI comes from R's bootstrap; the offset contrasts carry only the 0.006% render floor.

## Validity thresholds (a result outside these is not believable)

* **V1.** Every re-scored H must match its published `total_fg_pixels` within 0.1%.
  * A failing arm is excluded and named.
  * If any offset arm fails, Q2 is VOID. If more than two seed arms in a tier fail, that tier's Q1 is VOID.
* **V2.** Probe vs zero must agree within 0.1% on both ln H and ln S, or Q2 is VOID.
* **V3.** Re-scored σ_H must be within ±0.002 of the published value for its tier (0.0423 / 0.0608).

## Predictions and decision rules, fixed now

* **Q1 (pinned):**
  * "S less noisy" if R's 95% upper bound < 1;
  * "S noisier" if the lower bound > 1;
  * otherwise "no detectable difference".
  * **Prediction P1: S less noisy.** Confidence low-moderate: sub-threshold mass should not flip at the
    threshold, but seed noise here is mostly the fit relocating ink, which S also sees.
* **Q2:**
  * "S discriminates better" if D's lower bound > 1;
  * "worse" if D's upper bound < 1;
  * otherwise "no detectable difference".
  * **Prediction P2: no detectable difference.** Confidence low. I expect S to respond less
    (a ≈ 0.7) and to be less noisy (R ≈ 0.8), roughly cancelling.
* **Q1 replication (current tier),** same rule. **Prediction P3: S less noisy.**
* **Recommendation rule:** recommend S to villa only if all three hold:
  * Q1 pinned says "less noisy";
  * Q2 is not "worse";
  * the current tier is "less noisy" or has R < 1 by point estimate.

  Otherwise S is not recommended, and the report says which condition failed.

## Limits, stated now

* The offset sweep is one surface in one region. a(k) measures sensitivity to radial displacement, which is
  one kind of loss, not legibility in general.
* Neither metric is validated against labels here. The labels sit on segment meshes, not spiral fits.
* The current tier's three reused maps were made on 09-14 by the same patched scorer and are held to the
  same V1.

## Amendment 1 (2026-10-04, while the chain ran; before any pinned or offset result was looked at)

At commit time 3 of 29 arms had been scored. Only the chain log's "DONE" lines and one arm's V1 check (H
re-scored vs published, +0.0002%) had been read.

**Secondary analysis, descriptive, with no predictions: hard counts at lower thresholds.** villa's scorer
already takes `--fg-threshold`, so a lower threshold is adoptable **with no code change**. S needs one.
* For t ∈ {0.1, 0.2, 0.3, 0.4, 0.5}, H_t is counted from the same float16 maps (`scripts/soft_count_thresholds.py`).
  H_0.5 from float16 is a consistency check against the exact H.
* R(t) and D(t) are computed exactly as for S, with the same bootstrap seed and the same groups.
* **Reported as secondary.** It changes none of the registered verdicts and not the recommendation rule.
* **No threshold is recommended on this data alone.** Choosing the best of four after seeing them is
  selection. If one is cited, all are reported, and a recommendation would need a fresh test.
