# The registered ground truth is displaced — the held-out "chance" result is in question

**2026-08-07.** Reproduce: `uv run python scripts/probe_registration_offset.py`
Data: [`registration_offset_2026-08-07.json`](registration_offset_2026-08-07.json)

## Why this was measured

villa PR [#1280](https://github.com/ScrollPrize/villa/pull/1280) was closed 2026-08-06 by
`erdpx`: *"the provided ink registration example doesn't show the alignment working."*

That objection is correct, and for a worse reason than a presentation nitpick. The only
visual evidence we shipped, `overlay_vs_canon.png`, paints the registered GT **opaquely
over a thresholded model prediction**. On the held-out flagship that prediction is itself
near chance by our own leaderboard, so the image is structurally incapable of
demonstrating alignment — and painting GT on top hides the agreement it was meant to show.
Nothing in ScrollGT overlays GT against the CT imagery, and one of the three pixel targets
ships no overlay at all.

So we replaced the visual argument with a measurement.

## Method

A registration is correct only if GT-vs-prediction agreement is **maximised at zero
shift**. We scan Dice over pure translations and ask where the peak actually sits.

- Comparison surface is the distillation pipeline's **own** region-cropped teacher
  (`local_data/sota_distill/<frag>/<frag>_inklabels.png`, written by
  `repro/sota_data/distill_prep.py` for exactly this region). Using it keeps the probe's
  own crop conventions out of the answer — an earlier version of this measurement
  re-derived the crop with a hardcoded 4× level-2 factor, and re-running it through the
  pipeline's artifact changed nothing, which is what ruled that out as the cause.
- Every shift is scored on a **common interior crop** (margin 1000 px), not `np.roll` —
  wrapped content would otherwise contaminate the score.
- Search half-width must be ≥ ~1000 level-2 px. At ±400 the held-out peak clamped to the
  boundary (dx=400) and under-reported the offset; the script now warns when this happens.

## Result

| target | Dice @ 0 | Dice @ peak | peak shift (level-2 px) | ≈ level-0 voxels | gain |
|---|---|---|---|---|---|
| `scroll1_20230702185753` (train-exposed) | 0.453 | 0.603 | (−18, −44) | ~190 | +32.9% |
| `scroll1_20231210121321` (**held-out flagship**) | 0.321 | 0.530 | (76, **435**) | ~1766 | +65.1% |

Both peaks are interior and stable across search windows. The offsets differ per segment,
so this is not one global convention bug.

Rescoring the canon teacher at the corrected shift (binarised predictor, so these numbers
are comparable **to each other**, not to the threshold-swept leaderboard):

| | held-out, as published | held-out, shift-corrected |
|---|---|---|
| roc_auc | 0.582 | **0.718** |
| prevalence_lift | 1.599 | **2.760** |
| f1 | 0.321 | 0.530 |

## What this means

ScrollGT's README states: *"an honest ROC-AUC > 0.60 here would be news."* **A pure
two-degree-of-freedom translation clears that bar.**

The headline finding — "everything published reads at chance on the held-out segment" —
is therefore **not established**. It is substantially, and possibly entirely, an artifact
of a misregistered ground truth. Every downstream conclusion that rests on it inherits the
doubt, including the GT fine-tune negative (a model scored against displaced labels will
degrade toward the trivial predictor, which is exactly what we observed).

The filing (`docs/PRIZE_FILING_2026-07_SUBMIT.md`) explicitly ruled this out:

> *"The same registration quality let the good-teacher segment score 0.70, so the
> near-chance number is real, not a registration artifact."*

That inference does not hold. It assumed registration quality is a single property shared
across segments; the measurement shows the offsets are **per-segment** (~190 vx on one,
~1766 vx on the other), so one segment scoring well says nothing about the other.

`meta.json` reports a median residual of 7.85 voxels. The systematic translation is 23–230×
that, which means the residual statistic was measuring correspondence scatter and **never
constrained absolute placement**. A registration can have tight residuals and still be
bodily displaced; we shipped the former as evidence for the latter.

## ROOT CAUSE — found and fixed (same day)

**`repro/sota_data/register_run.py:26` — `LEVEL0_SHAPE = (50600, 36400)`**, a single
module-level constant applied to every segment. It is 20230702185753's level-0 surface
volume shape. 20231210121321's is **(51000, 39980)**.

Blame was arbitrated by checking the teacher rasters against the bucket: the canon
prediction tifs are **exactly** the level-0 surface volume shapes (50600×36400 and
51000×39980), so `distill_prep.py`'s `sy = th/lh` is exactly 4.0 with a shared origin.
The teacher crop is correct; **the registered GT was the misplaced artifact.**

`_region_in_mesh()` (on the live `warp_obj` path) maps the level-2 region into mesh
coordinates with `sy, sx = mh / (LEVEL0_SHAPE[0]/4), mw / (LEVEL0_SHAPE[1]/4)`. With the
wrong constant, **both the crop origin and the crop width** scale wrongly — so the emitted
label is translated *and stretched*: x by 9995/9100 (+9.8%), y by 12750/12650 (+0.79%).
That is why a translation-only correction only reached Dice 0.53; a pure shift cannot undo
a stretch.

Undoing the mapping analytically (`u' = k·u + x0·(k−1)`) confirms it:

| | Dice @ 0 | peak Dice | peak location |
|---|---|---|---|
| shipped GT | 0.321 | 0.530 | (76, 435) |
| corrected GT | **0.677** | 0.751 | **(23, −9)** ← at zero |

**The corrected held-out scores, canon teacher:**

| metric | as published | corrected |
|---|---|---|
| roc_auc | 0.582 | **0.814** |
| prevalence_lift | 1.599 | **3.268** |
| f1 | 0.321 | **0.677** |
| precision | 0.291 | 0.630 |
| recall | 0.357 | 0.730 |

The held-out segment now scores **better** than the train-exposed one (0.814 vs 0.724).
The "held-out collapse" was entirely an artifact of the constant. 20230702185753 was
unaffected by this bug — the constant is its own shape — which is exactly why the
cross-segment sanity check ("the other segment scores 0.70, so registration is fine")
could not detect it.

**Fix:** `LEVEL0_SHAPES` is now a per-segment dict; `_set_target()` binds it and **raises**
for any segment without a recorded shape rather than falling back to a default.
`register_run.py verify_shapes` checks every entry against the bucket (both verified OK).
Regression tests in `tests/test_sota_register_targets.py` pin per-segment shapes, the
no-fallback behaviour, and that `_region_in_mesh` actually tracks the shape.

**Still outstanding:** a second, smaller placement error remains — train-exposed (−18, −44),
corrected held-out (31, −10). Diagnosed below, not yet fixed.

## The residual offset — mechanism identified, fix NOT yet applied

`_region_in_mesh` converts the level-2 region into grid coordinates of `MESH_NEW` =
`<seg>-on-20230205180739-7.91um.tifxyz`, assuming that grid's extent is proportional to the
2.4 µm level-2 volume. **That assumption is false**, for two compounding reasons.

**1. Wrong mesh for the job.** Every segment also ships
`<seg>-on-20260411134726-2.4um.tifxyz` — and `20260411134726` is precisely the scan behind
the surface volume we score against (`2.4um-...-volume-20260411134726.zarr`). Both meshes
declare `scale: [0.05, 0.05]`, but each *relative to its own scan's level-0 grid*:

| mesh | grid | level-2 px per cell |
|---|---|---|
| `…-on-20260411134726-2.4um` (volume's own scan) | 2530×1820 | **exactly 5.00 × 5.00** |
| `…-on-20230205180739-7.91um` (2023 scan, what we use) | 776×559 | 16.30 × 16.28, anisotropic |

The 2.4 µm grid indexes the level-2 volume exactly. The 7.91 µm grid sits on a different
scan's pixel lattice, so mapping level-2 → grid through it is an approximation whose error
is segment-specific — which is exactly the signature we see (offsets differ in both
magnitude and sign between the two targets).

**2. Integer mesh-cell rounding.** With ~16 level-2 px per cell, `int(round(...))` on the
crop bounds shifts the content and mis-scales the crop span. Quantified: predicted net
displacement at region centre **(+11.7, −12.0)** px for held-out, **(+12.1, −12.0)** for
train-exposed. That matches the held-out `dx` (−10 measured) well, but the predictions are
nearly identical for both targets while the measurements are not — so rounding is a real
~12 px contributor, **not** the dominant term. The mesh choice is.

**A tempting fix was tested and FALSIFIED.** The natural repair — crop on the 2.4 µm grid
and read the old-frame xyz from the 7.91 µm grid at the *same normalised UV* — assumes the
two grids share a UV domain. They do not. Sampling both on a common normalised lattice
(83,668 paired points) and fitting a global similarity leaves a **median residual of 2137
voxels, 4.6% of the surface's 46,474-voxel extent** (fitted scale 3.236 vs the 3.296 implied
by 7.91/2.4). The two are independent flattenings of the same physical surface. Same-UV
sampling is not a valid bridge.

**And the redesign that would follow from it was ALSO tested, and it does not work.** The
plan was: define the region on the 2.4 µm grid (exact), then carry the points into the
old-scan frame with an *unpaired* 3D similarity before the NN bridge onto `original.obj`.
`original.obj`'s vertices are in the old frame (v spans 2294–4835 / 1850–5390 / 7–13695,
matching the 7.91 µm mesh bbox, not the 2.4 µm one), so crossing scan frames is unavoidable.

Fitting that transform (PCA + trimmed ICP, 4.03M vs 381k points) gives scale 0.30466 —
close to the 0.30341 implied by 2.4/7.91, so the fit is not wildly wrong — but a **median
residual of 81 old-scan voxels**. For comparison, the existing obj NN bridge has a residual
of **7.95** old voxels, and the current placement error is ~32 level-2 px ≈ **39 old
voxels**. Routing through the scan transform would therefore be *worse than what we have*.

**Why: the two scans' surfaces genuinely differ.** The residual is not bimodal (which would
indicate a trimmed-extent mismatch that better ICP could fix). It is broad:

| quantile | 5% | 25% | 50% | 75% | 90% | 99% |
|---|---|---|---|---|---|---|
| residual (old-scan vx) | 7.4 | 16.4 | 64.4 | 156.9 | 249.2 | 452.5 |

Only 32% of points land within 25 voxels; 17% are beyond 200. The 2023 and 2026
segmentations of this sheet are **materially different surfaces**, not the same surface in
two coordinate systems. No rigid or similarity transform can bridge them tightly.

## What this means: the residual is a floor, not a bug

The remaining ~30 level-2 px (~130 level-0 voxels ≈ 0.31 mm) offset is **not a defect
awaiting a fix**. It is an intrinsic uncertainty of the method — bridging 2023 hand labels
onto 2026 re-flattened geometry across two scans whose surface segmentations disagree by
tens to hundreds of voxels. The current proportional-grid mapping, crude as it is, is
already outperforming a principled 3D transform.

This should be stated as a **property of any registered-GT target built this way**, and it
bounds what the pixel targets can ever resolve. It does not affect the `LEVEL0_SHAPE`
conclusion: 1766 voxels was 13× this floor and unambiguously a bug.

**Open decision — the gate threshold.** `cmd_validate` now enforces placement at a default
of 8 level-2 px, and the corrected held-out target **fails it at 32.0 px** (marker removed,
scoring blocked). Setting the threshold at the measured floor instead would let the targets
through, and there is now positive evidence that such a floor exists. But relaxing a gate
because our data fails it is precisely the failure mode that produced the 2026-07 retraction,
so the threshold is deliberately left strict and the targets are left failing pending an
explicit, recorded decision.

## What this does NOT establish

- **The peak offset is not a correction.** It was fit against a model output, so it
  localises disagreement, not truth. The real corrective transform must be re-derived from
  the geometry, not from agreement with a prediction.
- **Blame is not yet assigned.** The two artifacts disagree; either `register_run.py`'s
  obj/tifxyz bridge places GT wrongly, or `distill_prep.py`'s `sy = th/lh` teacher crop
  places the prediction wrongly. Both pipelines feed the leaderboard, so the leaderboard is
  affected either way — but the fix differs completely depending on which it is. That is
  the open question.
- **A translation-only model may be incomplete.** Only pure shifts were scanned. Residual
  scale or rotation error would not show up here.

## Status

- **Done:** `LEVEL0_SHAPE` fixed and guarded; held-out target re-registered
  (enrichment 1.68 → 6.01) and the full leaderboard re-scored and published.
- **Diagnosed, not fixed:** the residual offset — wrong mesh for the region crop, plus
  ~12 px of integer mesh-cell rounding. Requires the redesign described above.
- **Not examined:** `scroll1_20230702185753_y7000_x4000`.
- **Void, needs retraining:** `arm C + GT fine-tune`, which was fine-tuned on the displaced
  label. Removed from the leaderboard rather than re-scored — and it should not be
  retrained until the residual is fixed, or it will just bake in the smaller error.
