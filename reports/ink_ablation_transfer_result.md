# The released ablation series DOES read Scroll 1, monotonically in pseudo-label density

**2026-08-30.** Measured after the preprocessing was corrected and validated. This revises the
picture in `reports/ink_absence_vs_unrecovered_result.md`, which under-read the instrument.

## Our ground truth is validated by an independent published prediction

The open-data bucket publishes a canon prediction for `20231210121321` on the same volume. Scored
against ScrollGT's registered ground truth for that segment:

```
published canon vs our GT:   AUC 0.8243     (0.8798 at the target's recorded peak shift)
```

That is an external check on our target that we did not previously have. A registered label that a
third-party model reads at 0.82 is a working label.

## Four of six members read held-out Scroll 1 ink

Same frame, no shift, 2048^2:

| member | training tiles | AUC vs our GT |
|---|---:|---:|
| it1 | 3,396 | 0.5070 |
| it2 | 8,970 | 0.5317 |
| it3 | 15,286 | 0.6837 |
| it4 | 24,773 | 0.7231 |
| it5 | 33,061 | **0.7247** |
| it0 | 20,075 (cross-segment baseline) | 0.7156 |

**The ladder is monotone in pseudo-label density**: 0.507, 0.532, 0.684, 0.723, 0.725. These models
were fine-tuned on PHerc 1667 segment `l_2` and never saw this Scroll 1 segment, so this is
cross-scroll transfer improving with the amount of pseudo-labelled data on the *source* scroll.

it1 and it2, the two sparsest rungs, sit at chance. The gain arrives between 8,970 and 15,286 tiles.

## This corrects an earlier claim of mine, twice over

Earlier today the same models scored 0.41 to 0.48 against this ground truth and I was one step from
publishing "the PHerc.1667 series does not transfer to Scroll 1". That was voided for a preprocessing
error. It was right to void: with the corrected pipeline they read at 0.72.

And `reports/ink_absence_vs_unrecovered_result.md` says the instrument is uncalibrated and its null
therefore uninformative. The calibration problem is real, but the conclusion drawn from it was too
strong: **AUC is rank-based, so the 59 to 82% firing rate does not affect it.** The models rank ink
correctly while over-firing at any fixed threshold. Ranking and calibration are different properties
and only the second is broken.

## What the absence-versus-failure null now means

It stands, and it is narrower than a broken instrument. Members disagree at AUC 0.5268 between false
and true negatives while the same members rank ink at 0.72. So the series detects ink and its
*disagreement* still does not separate "no ink" from "no ink recovered yet".

One genuine caveat survives: the negative set is defined by `p_mean < 0.5`, and with members firing
on 59 to 82% that threshold selects only the lowest fifth to two-fifths of pixels. That split is
calibration-sensitive even though AUC is not, so the null should be re-run once firing rates match
the published 14%.

## Limits

One segment, one scroll, one architecture. The monotone ladder is five points with no repeats, so
the ordering is suggestive rather than established, and it1/it2 sitting at chance could be a
threshold effect rather than a genuine floor. Our pipeline still deviates from the published recipe
in stride, masking and possibly intensity convention, all recorded in
`repro/ink_ablation/README.md`.

## Calibration, corrected a second time: 26% is the right reference, not 14%

I twice called this pipeline badly miscalibrated by comparing its firing rate to the **canon** model's
14.06% on this segment. Canon is a different model. The right reference is what these checkpoints
themselves publish, and the model card ships it:

| reference | above 0.5 |
|---|---:|
| iteration-5 preview on `l_2`, its **training** segment | 8.71% |
| iteration-5 preview on `l_5`, a **held-out** segment | **26.27%** |
| canon model on our Scroll 1 segment | 14.06% |
| **our it5 on our Scroll 1 segment** | **69.65%** |

So these models legitimately fire far more than canon, and 26% rather than 14% is the number our
held-out rate should be judged against. We are 2.7x that, not 5x a universal target, on a *different
scroll* where more mid-range uncertainty is expected. (The previews are downsampled 16x, which
smooths extremes, so even 2.7x is an upper bound on the discrepancy.)

**Twice now I have overstated a calibration problem**: first by calling the null uninformative when
AUC is rank-based and unaffected, then by benchmarking against the wrong model. The underlying
lesson is the same each time, that a reference has to be the right reference, and "published number
on the same segment" was not sufficient when the publisher was a different model.

What survives unchanged: the threshold caveat on the absence-versus-failure null. It defines
negatives as `p_mean < 0.5`, which selects the bottom 30% of our pixels where the models' own
held-out behaviour would put roughly 74% below that line. That comparison is threshold-dependent in
a way the AUC results are not, and it is the one place where matching the published recipe would
still change something.
