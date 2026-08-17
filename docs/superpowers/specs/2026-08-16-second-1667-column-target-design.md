# A second column target: the same reading on a different flattening

**Date:** 2026-08-16
**Status:** SUPERSEDED 2026-08-17 -- the premise below is factually wrong. `merged_v4` is a
whole-scroll merge across multiple windings, not a different flattening of the same material
as `w011_flatboi`; `w011_flatboi` is one winding inside that merge. Measured, not inferred:
the pre-registered transfer run found 0 of 22 columns clear all gates (floor 5), 21 of 22
had no real destination correspondence, and the one exception (col 22) still missed this
project's own genuine-correspondence benchmark by ~23x. No target was built; the family
stays at n=1. Full account: `reports/detector/w011_column_transfer.md`. This document is
kept as a record of the (incorrect) premise and is not corrected in place.
**Repos:** derivation in `vesuvius-autoresearch`, target ships to `../scrollgt` (public)

## Problem

ScrollGT's column family has exactly one target, `pherc1667_merged_columns`. That was
disclosed on 2026-08-15, and a single target cannot separate model quality from target
idiosyncrasy.

**A genuinely independent second column target does not exist in published artifacts**, and
this was checked rather than assumed:

- **PHerc 0172's** published reading image (`0172_banner_full.jpg`, 3200x533) is five
  *disconnected* ink patches on black with no annotations. The 1667 registration worked
  because the preprint figure carried labelled `col. N` bracket intervals; there is nothing
  here to extract column boundaries from.
- **Scroll 1's** (`paris4_banner.jpg`, 3200x840) is a continuous strip whose columns are
  visually obvious, but it is likewise unannotated. The only way to get boxes is to derive
  them from the ink — and the column metric asks whether a prediction carries more signal in
  columns than gutters, so boxes derived from an ink-detection output would make the target
  measure agreement with that output. That is the agreement-with-teacher circularity this
  project already corrected once, and it is disqualifying.

So the independent-reading axis is capped. What is *not* capped is a different and useful
question the current single target cannot answer: **does a column-level score survive a
change of flattening?**

## What this target is, and is not

PHerc 1667 has 20 segments in the open data. The existing target uses
`20260612121456-w011_20260108140509268_merged_v4_flatboi_straightened_v4` — a merged and
straightened flattening built from winding w011. The raw flattening of that same winding,
`20260108140509-w011_20260108140509268_flatboi`, is also published, and its mesh includes
`20260108140509-on-20251217075048-2.399um.tifxyz` — **the same scan at the same resolution**
as the merged target's tifxyz.

The two therefore differ *only* in flattening, merging and straightening. That isolates the
variable exactly.

**It buys:** evidence that a column-level score is (or is not) robust to the geometry a model
is handed — a real property of a benchmark that scores predictions on flattened surfaces.

**It does not buy:** an independent reading. Both targets rest on the same eight-papyrologist
consensus. A model that mislocates columns for reasons intrinsic to the reading will
mislocate them on both. **The target's own `meta.json` and the docs must say this**, or an
n=2 count implies an independence the pair does not have.

## Derivation

Not by re-registering figure strips, and not from ink.

Both flattenings are surfaces over the same 3D scan, so every grid cell has a 3D point in its
tifxyz. For each merged-grid cell inside a known column's `(gx0..gx1, text_band)` region,
read its 3D point, find the nearest point in the w011 tifxyz, and take the resulting w011
grid coordinate. A column's w011 extent is the envelope of its mapped cells.

This reuses the nearest-neighbour tifxyz bridge already proven in the pixel-GT registration
(`repro/sota_data/gt_register.py`), so it introduces no new technique, and column identities
stay anchored to the papyrological reading rather than to any model output.

Existing column geometry comes from `../scrollgt/data/pherc1667_merged_columns/columns.json`:
22 entries, each `{col, gx0, gx1, cross_strip, text_band, transcription, measured_line_pitch}`
on a 2061x30097 grid.

## Coverage and honesty about it

w011 is one winding. It will not carry all 22 columns, and columns clipped by its extent are
not scoreable. The target ships only columns whose mapped envelope lies **fully inside** the
w011 grid, records the excluded ones by number with the reason, and the scorecard names which
were scored — the same discipline the fiber family now applies to size classes.

The two columns already flagged `cross_strip` in the merged target (9 and 16, which span
strip-crop gaps) inherit that flag; if they map at all they ship flagged, not silently.

## Validation gates

Both must pass before the target ships, and both are reported in `meta.json`:

1. **Placement, teacher-free.** Line periodicity measured inside each mapped column, using the
   same `line_pitch_range` calibration the merged target carries ([85, 160] grid px). A mapped
   column with no periodic line structure is misplaced, whatever its residual looks like.
2. **Column-vs-gutter enrichment** against the w011 segment's own published `ink-detection`
   prediction. Teacher-dependent, so it is a supporting check rather than the gate — recorded
   with that caveat stated, because this project has twice mistaken a teacher-dependent
   diagnostic for a teacher-free one.

**Pre-registered stop condition:** if fewer than **five** columns map cleanly and pass both
gates, the target is not shipped. A column target with a handful of columns cannot support the
region-level AUC the family reports — the merged target's own note records ~±0.08 statistical
granularity at n=18 text columns vs 17 gutters, so a much smaller n would publish noise. In
that case the finding is written up and the family stays at n=1.

## Non-goals

- **No new metric.** The existing `score-columns` path scores this target unchanged.
- **No re-registration of the merged target.** Its columns are the input, not the output.
- **No claim of reading independence** anywhere in the shipped text.
- **No attempt at PHerc 0172 or Scroll 1.** The circularity above rules both out; that
  conclusion is recorded in the report, not re-litigated per target.

## Verification

- The mapped columns, rendered over the w011 valid mask, are visually inspected before
  shipping — the merged target shipped an overlay for exactly this reason.
- A test asserts every shipped column's envelope lies inside the w011 grid and that excluded
  columns are enumerated with reasons.
- A test asserts the target declares that it is not an independent reading, so the caveat
  cannot be dropped silently by a later edit.
- `scrollgt score-columns` runs against the new target with no network and no GPU, matching
  the family's existing guarantee.

## Risks

- **w011 may cover too few columns.** This is the most likely failure and the stop condition
  above handles it explicitly rather than by shipping a thin target.
- **The nearest-neighbour bridge may be poorly conditioned** where the two flattenings diverge
  most (straightening moves material). Residual is recorded per column, and a column whose
  mapping residual is an outlier relative to the rest is flagged rather than averaged in.
- **The pair is correlated by construction**, which is the point but is also the thing most
  likely to be over-read by a reader who sees "two column targets". Mitigated by the required
  disclosure, and by reporting the two as a robustness pair rather than as independent rows.
