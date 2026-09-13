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

---

# At what scale do the seeds disagree? About the scale the surface moves

**Added 2026-09-13.** Same three baseline arms, same volume frame, varying only the bin size.

## The number I nearly reported, and why I did not

At the 96×256 binning used above, **74.5%** of ink sits in bins all three seeds agree on, 17.0% in
bins two of three found, and 8.5% in bins only one found. That looked like a clean decomposition into
a stable core and a marginal fringe.

**It is an artifact of the bin size.** Sweeping the binning:

| bins (z × θ) | bin footprint | unanimous | 2 of 3 | 1 only |
|---|---|---:|---:|---:|
| 24 × 64 | 224 × 236 vx | 89.7% | 8.1% | 2.2% |
| 48 × 128 | 112 × 118 vx | 82.1% | 12.8% | 5.1% |
| 96 × 256 | 56 × 59 vx | 74.5% | 17.0% | 8.5% |
| 192 × 512 | 28 × 29 vx | 66.0% | 21.7% | 12.3% |
| 384 × 1024 | 14 × 15 vx | **43.2%** | 31.2% | 25.6% |

Quoting any single figure would have been quoting a choice. **"74.5% of recovered ink is stable" is
not a fact about the scroll; it is a fact about a bin.**

## The dependence is the finding

Agreement holds above ~50 vx and collapses as the bin approaches ~15 vx. **So the seeds place ink
consistently at coarse scale and inconsistently at fine scale, with the transition in the tens of
voxels.**

That is the same scale as something already measured. `reports/anchor_gate_verdict.md` found the
seed-to-seed **surface** displacement to be **~24 vx** (median point-to-surface distance between two
baselines, 24.01 and 23.98 across resampling seeds).

**The ink appears to move because the surface does.** The detector reads a sheet whose fitted position
differs by tens of voxels between seeds, so the ink it finds lands tens of voxels apart — which is
exactly where agreement breaks down.

## Stated as consistency, not causation

Two quantities agreeing in magnitude is not a mechanism. What would raise this above coincidence:

* the displacement is **directional** — if ink offsets between a pair of arms align with that pair's
  surface displacement vector, the link is established; this compares magnitudes only;
* ~24 vx is a **point-to-surface** distance, predominantly normal to the sheet, while ink offsets are
  tangential. These are different components of the same disagreement and need not match.

**What this does settle** is that the instability is not a uniform smear: it has a characteristic
scale, and that scale is small — tens of voxels on a strip spanning 2,337–2,466 in radius and 5,376
in z.

## Consequence

A two-seed check on `total_fg_pixels` compares totals. Two runs can score identically while disagreeing
about the location of a quarter of the ink at 56 vx resolution, and more than half of it at 15 vx. If
what matters is *where* the text is, the count cannot see that, and neither can the check villa
prescribes.
