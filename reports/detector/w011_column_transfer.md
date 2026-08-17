# PHerc 1667: transferring the 22-column reading onto the raw w011 flattening

**Date:** 2026-08-17
**Result: BLOCKED.** 0 of 22 columns clear all four gates. The pre-registered floor
(5) is not met. No target ships; the column family stays at n=1
(`pherc1667_merged_columns`).

## Bottom line up front

The premise this task was given — that `merged_v4` (the existing target's
flattening) and `w011_flatboi` (this run's destination) are two flattenings of *the
same material*, differing only in merge/straighten processing — **is wrong.**
`merged_v4` is a **whole-scroll merge across multiple windings**; `w011_flatboi` is
**one winding** inside that merge. They do not cover the same material, so a
column-to-column transfer between them is not testing "does a column survive a
change of flattening" — it is asking nearest-neighbor to invent correspondences for
material that, for most of the 22 columns, is not present in the destination at all.
That is a spec error in how the pair was described, not an error in the transfer
code or in this run. See "Diagnosis" below for the evidence.

## Method (unchanged from the plan)

Both flattenings store a 3D point per grid cell (tifxyz). For each valid source cell
inside a column's `(gx0..gx1, text_band)` box, look up its 3D point, find the
nearest 3D point on the destination flattening, and take that cell's grid
coordinates. A column's destination extent is the envelope of its mapped cells
(`scripts/transfer_columns_to_flattening.py`, Task 1, commit `11cbaf7c`). Column
identities come from the merged target's existing bracket coordinates
(`../scrollgt/data/pherc1667_merged_columns/columns.json`); no ink is read to place
columns.

This pair, if it had shipped, would have tested whether a column-level score
survives a change of flattening. It would not, even in principle, have tested
independence of reading: both targets rest on the same eight-papyrologist consensus
(Angelotti et al., CC BY-NC 4.0), and a model that mislocates a column for reasons
intrinsic to the reading would mislocate it on both.

## The two flattenings

| | merged_v4 (source, existing target) | w011_flatboi (destination, this run) |
|---|---|---|
| segment | `20260612121456-w011_..._merged_v4_flatboi_straightened_v4` | `20260108140509-w011_20260108140509268_flatboi` |
| tifxyz | `20260612121456-on-20251217075048-2.399um.tifxyz` | `20260108140509-on-20251217075048-2.399um.tifxyz` |
| grid shape (h × w) | 2061 × 30097 | **1975 × 736** |
| scale | 0.05 (1 grid px = 20 level-0 px, 2.399µm/px) | 0.05 (same) |
| scan / resolution | `20251217075048`, 2.399µm | `20251217075048`, 2.399µm (identical) |
| coverage | whole scroll, all windings, merged | **one winding** |

Both meshes sample the identical scan at the identical resolution — that part of the
premise holds. What does not hold is that they cover the same material: `merged_v4`
is a multi-winding merge and `w011_flatboi` is one winding. The destination is not
larger than the source in either axis (1975 < 2061, 736 ≪ 30097), so the plan's
grid-size stop condition does not fire — but the real problem isn't grid size, it's
that the two segments are different physical spans of the same scroll.

Source column widths (846–1250 grid px, measured from `columns.json`) already
exceed the destination's total width (736 grid px), which was the first visible
symptom before any transfer ran.

**Provenance note on the source mesh actually used:** this run's source tifxyz was not
fetched fresh from the bucket path in the table above. `scripts/evaluate_w011_column_target.py`
(`ensure_src_tifxyz()`) reuses a local, already-z-overrun-corrected copy at
`local_data/merged_w011_tifxyz` (from a prior render task, `repro/sota_data/merged_fullband_render.py`)
in preference to the raw bucket mesh, because it excludes points where the straightened
merged mesh's z overruns the scan volume — points that have no valid destination
correspondence either way, so this is strictly more correct for a transfer, not less. A
reader reproducing this run from the bare bucket path will get a different (very likely
larger) `n_source_cells` per column than tabulated here, because the raw bucket mesh has not
had those overrun points excluded.

## Method note: this run applied no residual filtering

Step 2's specified invocation runs `transfer_columns` with `max_residual=None`. Under
that setting `n_mapped` is identical to `n_source_cells` by construction — nothing
is ever dropped — so **`coverage = 1.000` for every column**, and the `coverage ≥
0.5` / `n_mapped ≥ 1000` floor did not discriminate anything in this run. This
confirms one of the coordinator's concerns directly: nearest-neighbor always returns
*a* point, so `coverage: 1.00` here measures "every source cell got mapped to
something," not "mapped well." The coverage floor Task 1's review added guards a
different, real failure mode (a column whose correspondences are mostly outliers
slipping through `fully_inside` on one lucky point, once `max_residual` filtering is
applied and drops the rest) — it was the right guard for that problem, but it is not
the mechanism that caught the failure in *this* run. The residual and the
x-collapse below are what caught it.

## Diagnosis: all 22 columns collapse onto the same ~650px destination band

`transfer_columns` reports every column `fully_inside: True` (no envelope touches a
grid edge; `n_edge_exclusion_only: 0`). Read alone that looks like full coverage. It
is not — and the clearest evidence is this: **every one of the 22 columns' mapped
`dst_gx0` is exactly 5**, and every `dst_gx1` falls in a narrow 590–661 range,
regardless of which source column produced it:

| col range | dst_gx0 | dst_gx1 range |
|---|---|---|
| 1–22 (all) | **5** (every column, no exceptions) | 590–661 |

Twenty-two source boxes that span 30097 grid px and 846–1250 px each individually,
drawn from bracket coordinates the merged target treats as physically distinct
columns, all land in the *same* ~650px-wide window of the destination grid. That is
not 22 columns each independently fitting inside a narrow grid — it is nearest-
neighbor routing every column's points to whatever is nearest inside `w011`'s
material, which for most source columns is not their own column's papyrus at all.
`dst_text_band` (the y-extent) does vary meaningfully by column, tracking the source
`text_band` — so there is some real per-column signal in the height dimension — but
the x-collapse means the envelopes are not trustworthy column locations.

**`median_residual` (3D distance, scan voxels, source point to nearest destination
point) confirms the same story and gives it a physical scale**, falling in a near-
monotonic trend from column 1 to column 22:

| col | cross_strip | n_mapped | median_residual (vox) | median_residual (mm) | dst_gx0 | dst_gx1 | periodicity (teacher-free) | enrichment (teacher-dependent, supporting only) |
|---|---|---|---|---|---|---|---|---|
| 1 | | 583,761 | 2990.7 | 7.18 | 5 | 596 | 0.070 | 1.63 |
| 2 | | 962,990 | 2948.5 | 7.07 | 5 | 655 | 0.118 | 2.26 |
| 3 | | 1,125,203 | 2970.8 | 7.13 | 5 | 656 | 0.245 | 2.38 |
| 4 | | 1,005,539 | 2954.3 | 7.09 | 5 | 593 | 0.168 | 1.62 |
| 5 | | 1,089,812 | 2922.6 | 7.01 | 5 | 596 | 0.167 | 1.80 |
| 6 | | 1,066,538 | 2824.3 | 6.78 | 5 | 590 | 0.172 | 1.69 |
| 7 | | 1,392,943 | 2734.1 | 6.56 | 5 | 656 | 0.185 | 2.59 |
| 8 | | 1,313,412 | 2597.3 | 6.23 | 5 | 596 | 0.080 | 1.85 |
| 9 | yes | 952,751 | 2467.4 | 5.92 | 5 | 609 | 0.065 | 1.90 |
| 10 | | 1,561,647 | 2378.2 | 5.71 | 5 | 656 | 0.139 | 2.71 |
| 11 | | 1,500,267 | 2259.5 | 5.42 | 5 | 610 | 0.097 | 1.97 |
| 12 | | 1,679,390 | 2148.2 | 5.15 | 5 | 656 | 0.129 | 2.69 |
| 13 | | 1,651,858 | 2024.7 | 4.86 | 5 | 656 | 0.169 | 2.76 |
| 14 | | 1,595,620 | 1892.2 | 4.54 | 5 | 610 | 0.100 | 2.08 |
| 15 | | 1,666,156 | 1679.5 | 4.03 | 5 | 610 | 0.036 | 2.14 |
| 16 | yes | 1,753,186 | 1518.9 | 3.64 | 5 | 610 | 0.037 | 2.11 |
| 17 | | 1,787,861 | 1305.3 | 3.13 | 5 | 610 | 0.026 | 2.19 |
| 18 | | 1,906,025 | 1118.5 | 2.68 | 5 | 610 | 0.048 | 2.08 |
| 19 | | 1,551,110 | 958.4 | 2.30 | 5 | 610 | 0.073 | 2.35 |
| 20 | | 1,860,135 | 704.9 | 1.69 | 5 | 610 | 0.056 | 2.19 |
| 21 | | 2,111,674 | 435.5 | 1.04 | 5 | 659 | 0.090 | 2.94 |
| 22 | | 2,066,716 | 185.4 | **0.44** | 5 | 661 | 0.110 | 3.04 |

Residual min/median/max across the 22 columns: **185.4 / 2203.8 / 2990.7 voxels.**
Falling from ~7.2mm (columns 1–8, physically implausible as genuine surface
correspondence) to ~0.44mm (column 22, the best of the batch). This matches the
scroll's spiral geometry directly: `w011` is nearest the material that column 22
represents and farthest from column 1's; nearest-neighbor still returns a "match"
for every other column, but those matches are onto whatever of `w011` happens to be
closest, not onto that column's own papyrus — which is exactly why they all collapse
into the same x-band above.

**For scale:** this project's validated pixel-GT bridge (`register_run.py`, the
teacher-free registration path) reports a real, accepted correspondence at **7.95
old-scan voxels** residual. Column 22's 185.4 voxels is **~23× that** — clearly
better than the rest of this batch, but not close to a correspondence quality this
project treats as genuine elsewhere. **Answering directly: no column in this run has
a residual small enough to be called a genuine correspondence by this project's own
existing standard.** Column 22 is the least-bad case, not a plausible pass.

## Teacher-free gate: line periodicity — ran to completion, 0 / 22 pass

**The periodicity gate did not error out and did not return `None` for any column.**
Every one of the 22 columns has a real, computed floating-point value in
`reports/detector/w011_column_transfer.json`
(`periodicity_teacher_free`), ranging 0.026–0.245. It ran once, per fully-inside
column (all 22 were fully-inside), against the destination segment's own raw surface
texture — a single mid-depth slice of its per-segment `surface-volumes` zarr
(pyramid level 2, block-downsampled 5× to grid resolution), inside the merged
target's calibrated band `[85, 160]` grid px. No detector model is involved in this
number.

**No column clears `periodicity > 0.5`.** The best score is column 3 at 0.245
(notably not column 22, the best-residual column); several (15–18) are below 0.05.
Under the literal per-column gate, 0 of 22 pass, and the gate is genuinely
uninformative-to-negative here rather than untested.

A caveat on how much weight to put on that null, independent of the x-collapse
diagnosis above: every prior use of `label_line_periodicity` in this project
(`register_run.py`, `gt_register.py`) was applied to a **registered human
ink-annotation label** warped into the target geometry — a near-binary mask, where a
correct placement scores 0.5–0.87 in this project's own validated runs. Column boxes
have no pixel-level ink label to warp, so this run applies the same function to raw
CT grayscale texture instead — a materially weaker signal (carbon ink is largely
invisible in raw CT without a trained detector). Concretely, the mechanism is a
binarization: `label_line_periodicity` thresholds its input with `lab > 127` before
computing the row-wise autocorrelation (`repro/sota_data/register.py`), which is a
sound way to turn a near-binary ink mask into a periodic signal but is a different
operation entirely on raw CT grayscale — there, `> 127` just means "pixels brighter
than the middle of the 8-bit range," with no relationship to ink. Column 22, the
best-residual column, still scores only 0.110 — consistent with either genuine
misplacement (which the residual and x-collapse independently already show) or a
texture channel that would score low even for a correctly-placed column. Given the
residual and x-collapse evidence stand on their own, this run does not need to
resolve that ambiguity to reach BLOCKED, but it should not be over-read as a second
independent confirmation — it is corroborating, not decisive on its own.

## Supporting check: column-vs-gutter enrichment (teacher-dependent) — informational only

Using the destination segment's own published `ink-detection` prediction, the ratio
of mean predicted-ink inside each mapped column to its adjacent 150-grid-px gutters
ranges 1.62–3.04, every column above 1.0. This is recorded as a **supporting,
teacher-dependent** figure only, per the plan — it does not gate the stop condition.
Given the x-collapse above, all 22 "columns" are drawing this ratio from largely the
same destination pixels, so the fact that it is uniformly >1.0 does not corroborate
per-column placement; it likely reflects that this segment's predicted ink is not
spatially uniform, not that 22 distinct columns were each correctly placed.

## Stop condition

A column counts toward the floor only if it clears **all four**: `fully_inside`,
`coverage ≥ 0.5`, `n_mapped ≥ 1000`, and the periodicity gate (`> 0.5`).

| gate | columns passing |
|---|---|
| `fully_inside` | 22 / 22 (uninformative here — see x-collapse) |
| `coverage ≥ 0.5` AND `n_mapped ≥ 1000` | 22 / 22 (uninformative here — `max_residual=None` makes this trivial) |
| periodicity `> 0.5` | **0 / 22** |
| **all four** | **0 / 22** |

**0 < 5 (the pre-registered floor). The stop condition fires: do not build a
target.** No `../scrollgt` files are created or touched. Tasks 3 and 4 of the plan
do not run. The column family stays at n=1 (`pherc1667_merged_columns`).

## Answers to the three verification questions

1. **Did periodicity compute, or error/return None?** It computed for every column.
   All 22 values are real floats (0.026–0.245); none is `None`, and nothing errored.
   The gate genuinely evaluated and genuinely failed everywhere — it is not an
   untested gate. (A message reached this run's author claiming periodicity was
   `None` for every column; that claim does not match the JSON on disk and is
   corrected here rather than repeated.)
2. **Does `coverage: 1.00` mean what it appears to?** No. It is a construction
   artifact of running with `max_residual=None` (as the plan's Step 2 literally
   specifies): with no filtering, `n_mapped` always equals `n_source_cells`, so
   coverage is 1.0 regardless of correspondence quality. The coverage floor added
   after Task 1's review guards a real, different failure mode (a residual-filtered
   column passing on a single lucky point) and was not the mechanism that caught
   this pair's failure. The residual and the x-band collapse were.
3. **Is any column's residual small enough to be genuine?** Column 22, at 185.4
   voxels (~0.44mm), is by far the best and the only one under 1000 voxels along
   with columns 19–21. Compared to this project's own validated pixel-GT bridge,
   which accepts 7.95 voxels as a genuine correspondence, 185.4 is roughly 23×
   larger. Not plausibly a genuine correspondence by the project's existing
   standard — the least-bad column in a batch where the destination segment simply
   does not contain most of the source material.

## Why this is a spec error, not an execution defect

The task's premise — "the same 1667 reading on a different flattening of the same
winding" — does not hold for this pair. `20260612121456-w011_..._merged_v4_...` is a
**merge across multiple windings** (its own segment name says so: `merged_v4`,
"straightened"); `20260108140509-w011_...` is **one winding**. A genuine second
flattening of the same material — the premise this task needs — would have to be
another flattening that covers the *same physical span* as `merged_v4`, not a
sub-span of it. This run establishes that `w011_flatboi` is not that: 21 of 22
columns' true papyrus is measurably absent from it (residuals 1000–2990 voxels,
1.7–7.2mm, and every one of the 21 collapses onto the same narrow destination band
regardless of source identity), and even the one column nearest a real match
(column 22) falls ~23× short of this project's own genuine-correspondence
benchmark.

**Inference vs. measurement, stated separately.** That `merged_v4` is a whole-scroll
merge across multiple windings is **inferred**, not measured here — from the segment
name (`merged_v4`, "straightened") and from the 41× width ratio between the two grids
(30097 vs. 736 grid px). This run did not open a third source (a scroll-level winding
map, say) to confirm the multi-winding claim directly. What **is measured**, and is the
load-bearing claim for the BLOCKED result regardless of the inferred one: the destination
does not contain most of the source material, full stop — that is what the residuals and
the x-collapse show directly, independent of why. Also worth naming, because it is
exactly the trap that produced this spec error in the first place: both segment names
contain `w011` (`20260612121456-w011_20260108140509268_merged_v4_flatboi_straightened_v4`
and `20260108140509-w011_20260108140509268_flatboi`). That shared substring is why the two
looked like "the same winding, differently flattened" at a glance — the premise this task
was given. Naming it here so the next person doesn't fall into the same read of the name.

**What to check before spending 20 minutes on the next attempt, in increasing order of
cost:**

1. **Two ~1 KB reads, seconds.** Every tifxyz directory ships a `meta.json` with an
   explicit 3D `bbox` (`[[xmin,ymin,zmin],[xmax,ymax,zmax]]`), and — as in this run — it is
   already on disk once the mesh is fetched, before any transfer runs. Read both candidate
   segments' `meta.json` and check that the destination's `bbox` actually contains (or
   substantially overlaps) the source columns' `bbox`. If it doesn't, stop there; a full
   transfer will not change that answer.
2. **A cheap empirical check, seconds, if step 1 looks plausible.** Subsample ~10k source
   cells (not all of them — that's most of the cost of a full run), bridge them through
   `transfer_columns_to_flattening.bridge_points` against the candidate destination, and
   look at the median residual. Compare it to this project's own validated correspondence
   benchmark of ~7.95 voxels (`repro/sota_data/register.py`, exercised in
   `register_run.py`) — a candidate whose subsampled median residual is anywhere near that
   is worth a full run; one that is 100s–1000s of voxels off, as this pair was, is not.
   Same answer this 20-minute run reached, in seconds.
3. **What kind of destination to look for.** Not another single-winding segment like
   `w011_flatboi` — look for another **whole-scroll merge or flattening** of PHerc 1667
   (i.e. something in the same class as `merged_v4` itself, covering all windings), since
   that is the class of object that can plausibly contain all 22 columns' material. A
   shared `w011`-style substring in two segment names is not evidence of shared coverage;
   step 1 or step 2 above is.
