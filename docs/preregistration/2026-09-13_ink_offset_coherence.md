# Pre-registration: is the ink offset between seeds spatially coherent, or noise?

**Written 2026-09-13, before computing anything.** Analysis of artifacts already on disk, so this
buys less than a registration written before data exists — it cannot stop me having seen the inputs.
What it does buy is a decision rule fixed before the number, which is the part I have repeatedly
needed.

## The question

`reports/ink_placement_in_volume.md` found that fits differing only by RNG seed place ink at r ≈ 0.70
in the scroll's own frame, with a characteristic disagreement scale of tens of voxels — close to the
~24 vx seed-to-seed **surface** displacement measured by the anchor gate. That report states plainly
that two magnitudes agreeing is not a mechanism.

**If the ink moves because the surface moves, the offsets should be spatially COHERENT**: neighbouring
regions of the scroll should be displaced in the same direction by similar amounts, because the sheet
is a continuous object. **If the disagreement is detector noise, the offsets should be independent
between regions.**

Coherence is therefore the discriminator, and it needs no assumption about direction conventions or
about which component of the surface displacement matters.

## What is measured

For a pair of arms, in volume (z, θ) space:

1. split the ROI into **z-slices**;
2. within each slice, find the angular shift Δθ that best aligns one arm's ink to the other's, by
   cross-correlation over ±15°;
3. collect the per-slice Δθ into a sequence ordered by z.

**The statistic: the lag-1 autocorrelation of that sequence**, i.e. do adjacent z-slices agree on
which way the ink moved.

## Null, and how it is built

The null is the same statistic after **shuffling the slice order**, which destroys spatial adjacency
while preserving the distribution of shifts exactly. 1,000 shuffles, and the reported p is the
fraction of shuffles whose lag-1 autocorrelation is at least the observed one.

This null is deliberately conservative: a real coherent field and an artefact that varies slowly with
z would both beat it. It separates *structure from noise*, not *surface from every other structured
cause*.

## Decision rule, fixed now

| outcome | conclusion |
|---|---|
| observed lag-1 autocorrelation **> null at p < 0.05** | offsets are spatially coherent — consistent with the ink moving with a continuous surface, and **inconsistent with independent detector noise** |
| **not** significant | no coherence detected at this slice count; the surface explanation gains no support and the magnitude agreement stays a coincidence |

**Reported for all three same-config pairs of the baseline arms** (s1-s2, s1-s3, s2-s3), and all three
are reported whatever they show. No pair is dropped.

## What this cannot do

* It cannot show the offsets match the *surface* displacement — only that they are structured. A
  slowly-varying detector artefact would also pass.
* Slice count is fixed at **24** now and will not be swept. Sweeping it until coherence appears is the
  failure mode this sentence exists to prevent.
* Angular shift is measured about a convention axis (the reference arm's centroid), so absolute Δθ has
  no meaning; only its variation with z is used.

## Prediction

**None registered.** My last three directional predictions about spiral metrics were wrong, twice in
opposite directions. The rule above decides this without one.
