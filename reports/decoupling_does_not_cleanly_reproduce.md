# On current villa the ink null reproduces, but the decoupling evidence does not

**2026-09-12.** Three ablated arms against the three current-code baselines, analysed by
`scripts/analyse_same_winding_current.py` exactly as committed before the first arm ran.
Registration: `docs/preregistration/2026-09-11_decoupling_on_current_code.md`.

## Result

| arm | `satisfied_area` | `total_fg_pixels` |
|---|---:|---:|
| nosamecur_s1 | 0.8557 | 2,893,440 |
| nosamecur_s2 | 0.8621 | 2,925,553 |
| nosamecur_s3 | 0.8593 | 2,852,335 |
| curbase_s1 | 0.8472 | 2,904,520 |
| curbase_s2 | 0.8494 | 2,901,177 |
| curbase_s3 | 0.8503 | 2,841,071 |

| endpoint | BASELINE | ABLATED | relative | p |
|---|---:|---:|---:|---:|
| `total_fg_pixels` | 2,882,256 | 2,890,443 | +0.28% | 0.7956 |
| `satisfied_area_fraction` | 0.8490 | 0.8590 | **+1.18%** | **0.0175** |

**VERDICT: NULL on reading**, no ink effect larger than **9.6%**. Bounded, not zero.

## The honest reading: this is weaker than the original, not a confirmation

The original study on the pinned tree found `satisfied_area` **falling** 0.69% (p=0.0027) while ink
did not move. That fall was the evidence. The registration had made satisfaction report-only because
removing 5,413 of the inputs it scores could inflate it trivially — *"a rise can mean less left to
satisfy"* — and a **fall is not subject to that confound**.

Here satisfaction **rose** 1.18% (p=0.0175): precisely the direction our own registration declared
uninterpretable. We cannot conclude the geometry improved, because the manipulation removed
constraints the metric is computed against.

So what reproduces is **the ink null alone**. The geometry signal that made the old result a
*decoupling* — two metrics demonstrably moving apart — did not reproduce; it moved into the direction
that carries no information.

**On current code, this study does not demonstrate decoupling. It demonstrates that removing 5,413
same-winding constraints does not measurably change reading.** That is a narrower claim and it is the
one we can defend.

## What this does to the four-case story

The corpus claim — four pre-registered cases of the two metrics moving independently, plus
r = -0.121 over 24 fits — **remains a statement about villa-spiral `6847063f`**. This attempt to
extend it to current villa produced an ink null and an uninterpretable geometry move, which is not an
extension.

Anything outward-facing should now say: the decoupling was measured on superseded code; on current
code the ink null reproduces and the geometry evidence does not. `docs/VILLA_DRAFT_metrics_disagree.md`
and `docs/PRIZE_FILING_2026-09_DRAFT.md` both need that correction before they go anywhere.

## Prediction: wrong again, in the opposite direction

Registered: *"ink NULL and satisfied_area FALLS — the decoupling reproduces."* Ink was null; the
geometry direction was wrong.

**This is the second consecutive study where I predicted the direction of `satisfied_area` and was
wrong, and the two errors point opposite ways.** On the pinned tree I predicted a rise (reasoning
from a 200-step smoke fit) and it fell. Here I predicted a fall (reasoning from the pinned-tree
result) and it rose. Each time the reasoning was plausible and each time it was worthless.

**Stop predicting this metric's direction.** Two failures with opposite signs is not bad luck; it is
evidence that I have no working model of what moves it. Register the endpoint and the decision rule,
and state no directional expectation for `satisfied_area`.

## Validity

* all three arms passed the registered non-blank control (46.8%, 48.2%, 47.9% nonzero);
* 240 mesh entries each, all ten outer windings, full 38,442-patch input — the manipulation is
  constraints-only;
* arms differ only in `same_windings.json` and seed; `abs_winding.json` untouched;
* fits and renders on villa `be09a8503`, whose sole hot-path delta from the baselines' `d8c5f488a`
  is inert here (shell-dir-crop, never exercised);
* uncontended fit times match the baselines (2h57m vs ~3h), so no arm was advantaged by scheduling.

Machine-readable: `reports/samewinding_current_verdict.json`.
