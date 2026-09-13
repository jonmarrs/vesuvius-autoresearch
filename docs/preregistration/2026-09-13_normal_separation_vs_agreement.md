# Pre-registration: does ink agree less where the two surfaces sit further apart?

**Written 2026-09-13, before computing anything.** Closes the gap named in
`reports/ink_offsets_are_not_coherent.md`: that report ruled out a *tangential* slide and stated it
was blind, by construction, to a **normal** displacement.

## The question

Two fits differing only by RNG seed place ink at r ≈ 0.70 in the scroll's frame. The anchor gate
measured their surfaces as ~24 vx apart, **predominantly normal to the sheet**. A normal displacement
moves the sheet through the volume without rotating it, so the detector samples different voxels —
which would change what ink is found without producing any angular shift.

**If that is the mechanism, ink should agree WORSE in regions where the two surfaces are FURTHER
APART**, and the disagreement should be a function of local separation rather than uniform.

## What is measured

For a pair of arms, per (z, θ) bin at the 96 × 256 binning already used:

* **separation** — the absolute difference in mean radius of the two arms' surface points falling in
  that bin, computed from the flat tifxyz about the shared convention axis. Radius stands in for the
  normal direction: for a spiral the sheet's normal is predominantly radial;
* **disagreement** — `|ink_A − ink_B| / (ink_A + ink_B)` for that bin, which is bounded in [0, 1] and
  does not depend on the arms' absolute ink totals.

Bins where either arm has no surface, or both have no ink, are excluded — they carry no information
about either quantity.

**The statistic: Spearman correlation** between separation and disagreement across bins. Spearman
rather than Pearson because neither quantity is expected to be normal and separation is heavy-tailed.

## Null

Bin labels shuffled, 1,000 times, breaking the pairing between a bin's separation and its
disagreement while preserving both distributions exactly. Reported p is the fraction of shuffles whose
|ρ| is at least the observed |ρ|.

## Decision rule, fixed now

| outcome | conclusion |
|---|---|
| **ρ > 0**, p < 0.05 | **Supported.** Ink agrees less where the surfaces are further apart — the normal-displacement mechanism explains part of the placement instability. |
| **ρ < 0**, p < 0.05 | Ink agrees less where the surfaces are CLOSER, which the mechanism does not predict; reported as a surprise, not folded into support. |
| not significant | **Not supported.** With the tangential form already refused, the surface explanation would have no remaining tested form, and the placement instability would stand unexplained. |

All three same-config baseline pairs are reported, whatever they show. None is dropped.

## What this cannot do

* Radius is a **proxy** for the sheet normal. It is a good one for a spiral and a poor one wherever
  the sheet runs radially; no attempt is made to compute true normals.
* A positive result shows association, not that the displacement *causes* the disagreement — both
  could follow from a third thing, such as regions where the fit is generally less constrained.
* Bin size is fixed at the 96 × 256 already in use and **will not be swept**. The consensus-fraction
  work showed how strongly such numbers move with binning, which is exactly why the choice is frozen
  before the result rather than after.

## Prediction

**None registered.** Four directional predictions on spiral metrics so far, three wrong. The rule
decides this.
