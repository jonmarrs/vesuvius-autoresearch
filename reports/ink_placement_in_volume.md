# Where the ink lands, measured in the scroll's own frame

**2026-09-13. EXPLORATORY — not pre-registered.** Follow-up to
`reports/ink_count_is_more_stable_than_ink_placement.md`, which compared ink in *strip* coordinates
and could not tell genuine movement from the two flattenings warping differently. This removes that
ambiguity. `scripts/compare_ink_in_volume.py`, `reports/ink_volume_all_arms.json`.

## Method

Every fit's flattened strip has a tifxyz beside it giving the volume (x, y, z) of each strip cell, so
ink can be placed in the scroll's frame — common to all arms, and something no flattening can rotate.
Ink is binned by (z, θ) about a **single shared axis** taken from the reference arm, and the maps are
compared between arms.

The grids align exactly: masks are 10× the tifxyz in both axes (4490×89820 against 449×8982). That
ratio is checked per arm and a mismatch skips the arm rather than mis-mapping it.

## Result

| comparison | n | mean r |
|---|---:|---:|
| **within config** (same manipulation, different seed) | 9 | **0.699** |
| **between configs** (different manipulation) | 27 | **0.701** |
| null (one map rotated in θ) | — | **−0.09** |

## Two findings, and the second reverses the worry that prompted this

**1. Ink placement is only ~0.70 reproducible between runs that differ solely by RNG seed** — in the
scroll's own frame, with the flattening explanation removed. The count agrees to 1.2% (CV 0.0124)
while the placement agrees at 0.70 against a null of −0.09. **`total_fg_pixels` is a stable summary of
a substantially unstable thing.**

**2. Changing the constraints moves the ink no more than changing the seed does** — 0.701 between
configs against 0.699 within. This *strengthens* our ablation nulls rather than undermining them. The
worry that prompted this work was that "+0.28% on a count" might hide ink relocating; it does not.
Removing 5,413 same-winding constraints, or 40 of 50 anchors, leaves the ink where reseeding would
leave it.

**The strip-space version got finding 2 wrong.** There, within (0.655) exceeded between (0.611) at
p = 0.046, which looked like constraints moving ink more than seeds do. In volume space that gap
vanishes. Different manipulations produce different flattenings, and the strip-space comparison was
partly measuring *that*. The p = 0.046 was flagged as marginal and post-hoc when published; it was an
artefact, and this supersedes it.

## Controls

* **Null is −0.09**, from rotating one map in θ — a transformation no flattening can produce.
* **Positive control:** the mapped ink totals match each arm's published `total_fg_pixels` to within
  0.2% (e.g. 2,834,781 mapped against 2,841,071 published for `curbase_s3`). The small deficit is
  cells whose tifxyz is invalid, which are excluded rather than counted at the origin.
* **A real bug this caught:** blocking mask tiles to tifxyz cells per-tile silently dropped two
  columns, because tiles are 16384 wide and 16384 is not divisible by 10. Every column after the
  first tile boundary would have been shifted. Concatenating at pixel resolution before blocking
  fixes it, and the shape check is what surfaced it.

## Limits

* Exploratory. No pre-registration, and the binning (96 × 256) was chosen once, not swept.
* The axis is a **convention** — the centroid of the reference arm's strip points — not a measured
  scroll axis. It is shared across arms, so it cannot manufacture a difference between them, but
  absolute θ has no meaning here.
* r ≈ 0.70 is agreement on a *binned* map. Finer bins would score lower and coarser higher; the
  comparison between arms is what carries, not the absolute value.

## What it means for the objective

A loop optimising `total_fg_pixels` is optimising a number that reproduces to ~1% while the ink under
it reproduces to ~0.70. Two runs scoring identically are not reading the same text. That is not an
argument against the objective — it is a measurement of how much of a scored improvement could be
relocation rather than gain, and it says a two-seed check on the count cannot see that at all.
