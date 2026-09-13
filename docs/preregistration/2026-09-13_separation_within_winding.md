# Pre-registration: the normal-displacement test, done in a frame that can see it

**Written 2026-09-13, after the previous attempt was found confounded and before this one computes
anything.** Replaces `2026-09-13_normal_separation_vs_agreement.md`, whose statistic averaged surface
radius across a (z, θ) bin containing several windings and therefore could not measure local sheet
separation (`reports/separation_test_was_confounded.md`).

## The fix

The flattened strip's **row** index is the across-winding coordinate: 449 rows spanning 10 windings,
~45 rows each. A single row therefore sits **within** one winding, which is exactly what the previous
binning destroyed by summing over rows.

**Premise checked before registering** — and disclosed, since it means I have seen these inputs:

* median radius per row correlates **0.957–0.973** between arms, so row index means approximately the
  same thing in each;
* median |Δradius| per row is **14.0 and 18.4 vx**, against the anchor gate's ~24 vx point-to-surface
  distance and the discredited 3.6 vx bin-mean. The right order of magnitude, which the previous
  statistic was not.

## What is measured

Arms are put on a common grid: rows are already within 1% (449/450/452) and are resampled to the
smallest; columns differ by ~3% and are resampled to a common length. Then per cell block:

* **separation** — the 3D distance between the two arms' `(x, y, z)` at that cell. Not a radius
  difference: the actual local offset between the two fitted sheets, which is the quantity the
  mechanism is about;
* **disagreement** — `|ink_A − ink_B| / (ink_A + ink_B)` over the same block.

Blocks where either arm lacks surface, or neither has ink, are excluded.

**Statistic: Spearman ρ** between separation and disagreement, null by shuffling block labels 1,000
times.

## Decision rule, fixed now

| outcome | conclusion |
|---|---|
| **ρ > 0, p < 0.05** | **Supported** — ink agrees less where the sheets are further apart, so normal displacement explains part of the placement instability |
| **ρ < 0, p < 0.05** | Opposite of the mechanism's prediction; reported as a surprise, never as support |
| not significant | **Not supported.** Both forms of the surface explanation would then have been tested and neither supported, and the instability stands unexplained |

All three baseline pairs reported, none dropped.

## Sanity check that must pass for the result to count

The median separation this produces must land in the **10–30 vx** range already measured by two
independent means. **If it comes back near 3 vx again, the frame is still wrong and the result is
void** — the same failure as last time, and it would be reported as void rather than as a null.

## What it still cannot do

* Association, not causation. Both quantities could follow from regions where the fit is less
  constrained.
* Block size is fixed at **8 × 8 cells** now and will not be swept. Three results in this thread have
  already moved with binning; the choice is frozen before the number.
* Row correspondence is approximate (r ≈ 0.96), so some separation is row misalignment rather than
  sheet displacement. That inflates separation, and would bias toward finding an association — so a
  **null is the safer conclusion here and a positive one carries this caveat**.

## Prediction

**None registered.**
