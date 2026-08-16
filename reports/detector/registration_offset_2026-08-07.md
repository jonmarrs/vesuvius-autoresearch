# The held-out "chance" result was a misregistration — found, fixed, reversed

**2026-08-07.** Reproduce: `uv run python scripts/probe_registration_offset.py`
Data: [`registration_offset_2026-08-07.json`](registration_offset_2026-08-07.json)

> **Resolution, for readers who want it up front.** A hardcoded `LEVEL0_SHAPE` applied one
> segment's geometry to every segment, displacing the held-out label ~1766 level-0 voxels.
> Fixed, re-registered, re-scored: the canon teacher goes **0.563 → 0.753 ROC-AUC** and the
> clean held-out students **0.553/0.558 → 0.731/0.746**, against an all-positive floor of
> 0.518. The "everything reads at chance held-out" headline is **retracted — it inverts.**
>
> A **placement gate** now enforces that agreement peaks at zero shift (threshold 48 px,
> 9× below the bug it catches); nothing tested placement before, which is how this shipped.
> A smaller residual is **closed as an irreducible floor**, not a pending bug: the 2023 and
> 2026 segmentations of this sheet are materially different surfaces. It is published as
> each target's resolution limit — **0.31 mm** held-out, **0.45 mm** train-exposed. The
> train-exposed target clears the gate by only 1.4 px; the threshold was not raised for it.
>
> The sections below are the investigation in the order it happened, so the early framing
> ("in question", "not established") reflects what was known at the time.

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

## A SECOND copy of the bug, found 2026-08-14

Fixing `register_run.py` was not enough. **`gt_register.py` carried its own hardcoded
`LEVEL0_SHAPE = (50600, 36400)`**, applied to every segment, and it survived the original
fix because nobody grepped for other copies.

It feeds the GT fine-tune, whose four training regions are:

| region | true level-0 | assumed | error |
|---|---|---|---|
| `20230702185753` ×2 | (50600, 36400) | (50600, 36400) | none from this bug |
| `20231005123336` ×2 | **(34880, 97280)** | (50600, 36400) | **x off by 167%**, y by 31% |

So the GT fine-tune trained on two regions whose labels were displaced by a 167% x-scale
error, plus two regions on the segment we now know is the worse-placed one (46.6 px and a
gate-failing 53.3 px). **That is very likely the whole of the "fine-tuning on GT makes
reading worse" negative** — the model was fitting garbage, and the result was already
retracted on weaker grounds.

Note the shape of `20231005123336`: 34880×97280 is *wide*, where 20230702185753 is *tall*.
The assumed shape was not merely wrong, it was the wrong aspect entirely.

**Fix.** `LEVEL0_SHAPES` now lives once, in the dependency-free `register.py`, with a
`level0_shape(seg)` accessor that raises rather than guessing. `register_run.py` re-exports
it; `gt_register.py` imports it and now takes `seg` in `_region_in_mesh`. All three shapes
verified against the bucket. Three regression tests: one greps the package for any
reappearing `LEVEL0_SHAPE = (...)` literal outside its home, one pins that `gt_register`
uses the shared accessor and that both fine-tune training segments are recorded, one fails
if two segments share a shape (the copy-paste signature).

The lesson generalises past this constant: **when a bug is caused by a hardcoded value,
grep for other copies before calling it fixed.**

## The withheld target was withheld for the wrong reason (2026-08-14)

`20231005123336_y4000_x2500` was withheld in 2026-07 on the stated grounds that *the canon
teacher is chance-quality there* (enrichment ≈ 1 for all four orientation candidates,
0.79–1.02), leaving the label's orientation unverifiable.

That enrichment collapse was the `gt_register.py` copy of the hardcoded-shape bug. This
segment's true level-0 is 34880×97280 against the assumed 50600×36400 — a **167% x-scale
error** — so the label was scattered, and a scattered label enriches at ≈1 against any
teacher. Re-registered with the fix:

| | 2026-07 (buggy) | corrected |
|---|---|---|
| teacher-enrichment | ≈1 (0.79–1.02, all four conventions) | **4.88** |
| residual | — | 8.10 |
| periodicity | — | 0.865 |
| **placement** | not measured | **57.5 px / 0.55 mm — FAILS the 48 px gate** (corrected 2026-08-15, see the end of this report) |

**The teacher was never chance-quality on that segment; our registration was broken.** The
target stays withheld, but now on a measured criterion (placement) rather than a mistaken
one.

Its sibling `20231005123336_y7000_x4000` drops earlier, at prep: periodicity 0.556 and a
registered ink fraction of **0.0005** — essentially no ink lands in the region at all.

### Consequence: the GT fine-tune cannot be retrained on current data

All four of `gt_finetune.py`'s training regions are now measured:

| training region | status |
|---|---|
| `20230702185753` y4000_x2500 | placement 46.6 px — marginal pass (1.4 px of headroom) |
| `20230702185753` y7000_x4000 | placement 53.3 px — **fails** |
| `20231005123336` y4000_x2500 | placement 57.5 px, ±1 px (corrected 2026-08-15) — **fails** |
| `20231005123336` y7000_x4000 | **drops at prep** (periodicity 0.556, ink 0.0005) |

At best one marginal region survives. Retraining would repeat the original mistake with a
smaller error, so the fine-tune stays retired until there is training GT that passes
placement — which, given the cross-scan floor, likely means a different segment rather than
a better bridge.

### The pattern, third instance

Three times now a gate or diagnostic fired correctly and the failure was attributed to the
data instead of the code:

1. the enrichment gate failed at 1.68 on the held-out target → blamed a "weak teacher",
   worked around with a teacher-free gate. It reads 6.01 on the fixed pipeline.
2. this segment's enrichment sat at ≈1 → blamed a "chance-quality teacher", target withheld.
   It reads 4.88 on the fixed pipeline.
3. a tight 8-voxel residual was read as evidence of correct placement → it never measured
   placement at all.

The common shape is not carelessness about measurement; it is **explaining away an
instrument that disagrees with us**. The instruments were right every time.

## Gate threshold: 48 px — decided 2026-08-07

`cmd_validate` enforces placement at **48 level-2 px** (`MAX_PLACEMENT_OFFSET_L2PX`). The
corrected held-out target passes at **32.0 px** and has been re-scored; numbers are
unchanged (the GT did not move — only the gate did).

The number is derived from the floor above, not reverse-engineered from our data:

| quantity | level-2 px | level-0 vx | mm | note |
|---|---|---|---|---|
| ideal | ~0 | 0 | 0 | unreachable across scans whose segmentations differ |
| held-out target | 32.0 | 128 | 0.31 | PASSES, comfortable margin |
| train-exposed target | **46.6** | 186 | **0.45** | PASSES by only **1.4 px** |
| **gate threshold** | **48** | 192 | 0.46 | |
| `LEVEL0_SHAPE` bug | 435 | 1740 | 4.18 | **9× the threshold** — caught wide |

**The train-exposed target is uncomfortably close to the line**, and that is worth stating
rather than glossing. It was *not* affected by the `LEVEL0_SHAPE` bug — the hardcoded
constant was its own geometry — so its 46.6 px is a separate matter: either the cross-scan
floor varies by segment more than the held-out figure suggested, or that target carries an
additional, unisolated defect. **The threshold was not raised to give it headroom.**

### The offset field is non-rigid — and the global number understates it

The ~(−30, −31) px "uniform excess" logged earlier as a lead is **falsified**. Measuring
placement per 768 px tile (`scripts/probe_placement_field.py`) shows the offset is not a
translation at all:

| target | global | dy mean ± sd | dx mean ± sd | worst tile | gate |
|---|---|---|---|---|---|
| `20230702185753` y4000_x2500 | 46.6 px | −13.8 ± **26.8** | −38.0 ± **33.0** | ~102 px | passes by 1.4 px |
| `20230702185753` y7000_x4000 | **53.3 px** | −22.3 ± 21.9 | −51.7 ± 13.2 | ~102 px | **FAILS** |
| `20231210121321` held-out | 32.0 px | +32.3 ± 8.2 | −6.6 ± 9.5 | ~50 px | passes |

### It is segment-wide, not region-wide

The third pixel target (`y7000_x4000`) had shipped with **no placement verification at all**.
Measured, it fails the gate at 53.3 px / 0.51 mm. So **both** regions of segment
`20230702185753` are poorly placed, while `20231210121321` is 3–4× tighter. This is a
property of that segment's 2023-vs-2026 surface disagreement, not of any one region, and it
means `20231210121321` is currently the only pixel target worth standing behind.

Note the irony: `20230702185753` is the segment the original filing used as its reassuring
reference ("the other segment scores 0.70, so registration is fine"). It is in fact the
worse-registered of the two.

A plane fitted to the field leaves residual scatter essentially equal to the raw scatter, so
this is neither a constant offset nor a linear scale error. It is **non-rigid**, exactly as
the cross-scan surface-disagreement account predicts — and it closes the search for a
convention bug on the train-exposed target. There isn't one.

**The consequence is a disclosure problem, not a code problem.** A single global placement
figure is optimistic: the train-exposed target reports 46.6 px globally while individual
tiles run to ~100 px (**~0.96 mm**). Local error there is roughly 3–4× the held-out target's.
Per-target scatter is therefore now published alongside the global peak; quoting the peak
alone would understate the uncertainty a user is exposed to.

The honest tension is worth naming: relaxing a gate because our data fails it is exactly
the move that produced the 2026-07 retraction. What makes this different is that the floor
was *measured independently* — the cross-scan surface disagreement is a property of the
data, established before the threshold was picked, not an explanation invented afterwards.
The safeguard is the margin: at 48 px the gate still catches the real bug nine times over,
and `tests/test_sota_register_targets.py` fails if that margin is ever eroded.

**Tightening this is welcome** as the cross-scan bridge improves. **Raising it to
accommodate a failing target is not**, and the test enforces that.

Consequence for users: **~0.31 mm is the resolution limit of the pixel targets**, now
published as a spec of each target rather than a footnote. Features closer together than
that cannot be scored reliably, and all absolute scores are mild lower bounds.

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
- **Closed as a floor, not a bug:** the residual offset. Two candidate fixes tested and
  falsified; the cross-scan surface disagreement makes ~0.31 mm irreducible for this
  method. Now published as each target's resolution limit.
- **Done:** placement gate (`register.placement_peak`, enforced in every gate mode,
  threshold 48 px derived from the floor). Held-out target re-validated and re-scored.
- **Not examined:** `scroll1_20230702185753_y7000_x4000`.
- **Void, NOT retrainable:** `arm C + GT fine-tune`, which was fine-tuned on the displaced
  label. Removed from the leaderboard rather than re-scored. This entry previously made
  retraining conditional on fixing the residual; that condition was moot, because the
  residual is closed above as an irreducible floor. Overriding it on 2026-08-15 exposed the
  real blocker: there is no training set. Exactly one Scroll-1 segment is labelled,
  re-flattened and correctly placed, and it is spent as the held-out evaluation target. See
  [gt_training_data_exhaustion_2026-08-15.md](gt_training_data_exhaustion_2026-08-15.md).

## Correction: the withheld region's placement is 57.5 px, ±1 px (2026-08-15)

The `20231005123336_y4000_x2500` placement published above as 55.1 px / 0.53 mm was a
hand-run measurement that no committed path reproduces. The commit that recorded it changed
only this report — no script, no code. The segment is not in `register_run.TARGETS`, so
`cmd_validate` never measured it, and `gt_prep_fragment` did not gain a placement check
until after that commit landed.

Re-run from committed code, the registered label itself is unchanged: `residual` 8.1026 and
`periodicity` 0.8648 reproduce the figures in the table above exactly, and the teacher crops
in `sota_distill` and `sota_xscroll` are byte-identical. The label and the reference are not
the difference. The search window is, because the agreement peak is broad:

| `placement_peak` parameters | peak | offset |
|---|---|---|
| defaults (`max_shift=256, coarse=4, refine=8`) | dy=56, dx=−13 | **57.49 px** |
| `coarse=2, refine=4` | dy=56, dx=−13 | 57.49 px |
| `max_shift=128` | dy=55, dx=−13 | 56.52 px |

**The reproducible figure from committed code at default parameters is 57.5 px / 0.55 mm.**
Across search windows the peak sits between roughly 56.5 and 57.5 px, so this offset is
determined to about ±1 px and should not be quoted to three significant figures.

A broad peak is itself consistent with a poorly placed label — a correctly placed one peaks
sharply at zero. Every value above fails the 48 px gate, so **no conclusion anywhere
changes**: the ScrollGT target stays withheld, the region stays excluded from
`gt_finetune.py`'s training set, and the 2026-08-15 exhaustion finding is unaffected. Only
the number and the precision it may be quoted to change.
