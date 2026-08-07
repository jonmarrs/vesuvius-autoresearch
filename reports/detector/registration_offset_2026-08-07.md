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

Root-cause: re-derive the region crop directly from the level-2 zarr shape to arbitrate
between the two pipelines, then re-run the full leaderboard against corrected targets.
Until then, the held-out leaderboard rows should be read as **withdrawn, not confirmed**.
