# Spiral ink objective: what we measured, with every floor attached

**2026-08-31.** One page over nine reports written across two days. Each claim is paired with the
floor it must clear, because the floor is what several of these results turned on, and getting the
floor wrong caused two reversals in a single afternoon.

## The floors, established first

| floor | value | applies to |
|---|---:|---|
| pipeline non-determinism | **1.42%** | two renders of the SAME meshes, and same-fit comparisons |
| seed spread, `2*CV`, n=4 | **21.7%** | two DIFFERENT fits |
| duplicate-coverage baseline (full fit) | **0.0897 to 0.1042%** | gap>=2 overlap in any converged fit |
| duplicate-coverage baseline (10-winding span) | **0.00%** | the span all arms are measured on |

`reports/pipeline_determinism_and_which_floor_applies.md`, `reports/seed_spread_four_fits.md`.

## Findings

**1. The objective can be inflated by coverage that reads nothing new.**
Duplicating all ten windings, with occupied cells byte-identical to baseline so zero new papyrus is
read, raises `total_fg_pixels` **+92.47%** while `overall_fg_fraction` moves **-0.00044**. 65x the
applicable floor. `reports/duplicate_coverage_inflates_the_objective.md`.

**2. The metric cannot separate fake growth from real growth.**
A duplicated eleventh winding (+12.59%) and a genuinely new eleventh winding (+12.83%) land **0.24
percentage points apart**. Like-for-like, needs no floor.

**3. Neither structure score catches it.**
`line` and `column` move as much or more for the honest arm than the duplicate. They fail this
failure mode. This weakened a suggestion I had already made upstream in villa#1658.

**4. The objective is not broken: it does reward a better fit.**
A 100-step fit scores **-59.5%** against a 30,000-step one, **2.7x** the different-fit floor.
`reports/objective_does_track_fit_quality.md`. Gameable and working are both true.

**5. It is noisy between equally good fits.**
Four fits differing only in seed, satisfaction indistinguishable (0.8382 to 0.8404), give
`total_fg_pixels` CV **0.1086**, worst pair **25.3%**. A single-run gain below ~21.7% is
uninterpretable, which is why `autoresearch.md`'s two-seed check is load-bearing, not merely prudent.

**6. A three-second geometric check separates what no ink metric can.**
Across five arms, `total_fg_pixels`, `fg_fraction`, `line` and `column` all overlap between
duplicated and honest; gap>=2 winding overlap separates cleanly (8.37 to 100% against 0.00%). It
costs 3 s on a 120-winding fit against ~12 min for one render and score, needs no ink volume, scorer
or GPU, and runs before any render. `reports/a_cheap_guard_the_metrics_lack.md`.

**7. Duplicate coverage is introduced by fitting, and concentrates in the outermost windings.**
Median wmax 126, 79.9% involving a winding at or beyond w120, reproducible across five fits with
median radius varying by 13 voxels. **Its cause is unknown**: the extrapolation explanation first
offered was withdrawn on 2026-09-01 when the arithmetic behind it proved invalid.
`reports/duplicate_coverage_is_an_outer_winding_phenomenon.md`.

**7b. It is introduced by fitting, not inherited, at every scale tested.**
Exactly 0 gap>=2 cells in the 100-step configuration at quant 1, 2 AND 4; nonzero at all three in
converged fits (242 / 1,764 / 10,345). gap-1 is background, near-identical between the two (627 vs
623 at quant 1), which is why it is excluded. Duplicate coverage is also *more* seed-reproducible
than the objective it can inflate (CV 0.0667 against 0.1086). The absolute figure is a proximity
measure at the chosen quantisation and must be quoted with it.

## What is NOT established, and matters

**Reachability through a fit is unproven, and the search for it is CLOSED.** Every duplicate arm
copies mesh folders, which villa's loop cannot do; it edits `fit_spiral.py`. Two attempts to induce
overlap through a fit, each a verified single-variable change:

* `loss_weight_min_spacing` 2.0 -> 0: duplicate coverage **unchanged** (0.10%);
* `loss_weight_dense_spacing` 12.0 -> 0: duplicate coverage **fell** to 0.04%, the opposite of the
  registered prediction.

Under the stopping rule registered before the second arm, the search ends rather than continuing to a
third knob. **Fit-produced duplication could not be induced by the obvious means.** That is weak
evidence an optimiser would not stumble into the exploit, and it belongs beside finding 1 rather than
buried. `reports/two_nulls_fit_produced_duplication_not_induced.md`.

**A third arm (`output_winding_margin` 4 -> 0) is VOID**, not a null: its verification condition
could not fire, because the observable is clamped by a config constant.
`reports/margin_arm_void_and_a_premise_withdrawn.md`.

**The satisfaction guard is untested.** `autoresearch.md` names three checks; this work tests two.
Mesh-level duplication leaves the fit untouched by construction, so satisfaction cannot respond. It
may well catch fit-produced duplication, and nothing here says otherwise.

**Nothing here observes villa's loop.** These are properties of the metric, not evidence any run has
exploited them.

## Provenance

Every finding is pre-registered with its decision rule fixed before the data, and the analysis code
for the seed spread was written before the fits finished. The corrections are in the reports rather
than tidied away: two results withdrawn and one reinstated, one prediction (arm D) recorded as a
miss, two nulls against predictions, one arm voided, and one explanation withdrawn.

**A pattern worth carrying forward:** all three verification conditions registered for the fit arms
were mis-specified, each written from a plausible reading of the code rather than from checking what
the observable actually does. Two were caught, one produced a void arm and a withdrawn premise. The
fix is to confirm an observable responds to a manipulation before spending the GPU time, not to
guess better.

Reproduce: `repro/spiral_render/`, `scripts/measure_winding_overlap.py`,
`scripts/analyse_seed_spread.py`. All from published artifacts.
