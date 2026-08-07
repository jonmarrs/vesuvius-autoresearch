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

**Still outstanding:** the train-exposed target retains a smaller (−18, −44) offset that
this bug does not explain, and the corrected held-out peak sits at (23, −9) rather than
exactly zero. A second, smaller placement error remains. The targets must be regenerated
from the fixed pipeline and the full leaderboard re-run before any of these numbers are
republished as final.

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

## Next

1. Regenerate all three `scroll1_*` targets from the fixed pipeline (`warp_obj` → `validate`).
2. Chase the residual (−18, −44) / (23, −9) offsets — a second, smaller placement error.
3. Re-run the full leaderboard and republish. **The corrected numbers above are a
   preview from an analytic undo, not a pipeline re-run** — they should not be quoted as
   final results until step 1 lands.

Until then the published held-out rows stay **withdrawn**, and the corrected ones are
**provisional**.
