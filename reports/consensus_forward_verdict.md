# VOID: the validity gate rejected an arm that shows no sign of being wrong

**2026-09-14.** Registered in `docs/preregistration/2026-09-13_consensus_forward_prediction.md`,
analysed by code committed before the first of the three new fits started.
`reports/consensus_forward_verdict.json`.

## The registered outcome

**VERDICT: VOID.** `curbase_s6` scored `total_fg_pixels` = 3,454,937, outside the registered gate of
2,700,000–3,050,000. The registration states plainly that a gate failure yields VOID, that this **is
not a null result**, and that the comparison does not mean anything.

That is the outcome. What follows does not change it.

## What the numbers would have been

Disclosed because hiding them would be worse, and labelled because they are not claimed:

| quantity | value |
|---|---:|
| cross-triplet single-vs-single | **0.700** — inside the 0.65–0.78 gate |
| **consensus vs consensus (3 seeds each)** | **0.876** |
| predicted by the independent-noise model | 0.884 |
| registered CONFIRM range | 0.86–0.92 |
| registered supported band | 0.884–0.904 |

**0.876 sits inside the CONFIRM range.** Had the gate not fired, this would have read CONFIRMED. It
is not being reported as confirmation, and the model is not being treated as supported.

## The uncomfortable part: the gate is probably the thing that is wrong

`curbase_s6` shows **no independent sign of being a bad arm**:

| check | s6 | the other five |
|---|---|---|
| `satisfied_area` | 84.7% | 84.7–85.2% |
| strip pixels | 414,313,800 | 403M–424M |
| non-blank control | 47.4% | 46.7–48.2% |
| render attempts | 1 (no retry) | 1 |
| **mean placement r vs others** | **0.726 — highest of all six** | 0.665–0.744 |

Its ink is 16% denser and its line and column scores are unremarkable, so the extra ink is probably
not letterform — but **spatially it agrees with the other arms better than any of them do.**

And the gate's bound was built from the spread of `s1–s3` alone:

| | CV | |
|---|---:|---|
| `s1–s3`, which calibrated the gate | 0.0124 | 3 arms, df=2 |
| all six arms | **0.0740** | 6 arms |

**I flagged that this spread was probably too tight before s5 and s6 existed**
(`reports/s4_is_high_a_watch_item.md`), having already retracted one CV that afternoon for exactly
this reason. I then built a gate on it anyway.

## So what is the honest position

**The study is VOID and the prediction is untested.** A gate calibrated from three fits rejected a
fourth, fifth-and-sixth-arm spread it was never wide enough to contain. That is a mis-calibrated gate,
not a corrupt arm — but **recognising that after seeing the result is exactly the reasoning a gate
exists to prevent**, and it cannot be used to reinstate the number.

What it does mean is that the gate should not simply be widened and the analysis re-run. That would be
choosing a threshold to admit the data I have. **A re-test needs the ink spread measured first, from
arms fitted for that purpose, and a gate set from it before any comparison is computed.**

## What survives

* The **cross-triplet single-vs-single check passed at 0.700**, inside its registered 0.65–0.78. The
  two triplets are comparable in placement terms; it was only the ink-count bound that failed.
* `curbase_s4/s5/s6` are sound arms and remain usable for anything not gated on that bound.
* The independent-noise model is **neither confirmed nor refuted** by this run.

## The lesson, which is the opposite of the last one

Two days ago a validity threshold saved a result from being a false positive
(`the_sanity_check_caught_a_false_positive.md`). **Here a validity threshold destroyed a result that
was probably fine.** Gates are not free, they are not automatically conservative, and one calibrated
on too little data fails in whichever direction its calibration was wrong.

**Calibrate a gate from a spread you have actually measured at the sample size you will face.** Three
fits did not entitle me to a bound on six.
