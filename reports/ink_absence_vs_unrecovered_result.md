# Absence versus unrecovered: no signal found, on an instrument that is not calibrated

**2026-08-30.** The pre-registered analysis in
`docs/preregistration/2026-08-30_ink_absence_vs_unrecovered.md` was executed in full. Result below,
followed by the reason it should not be reported as an answer to villa's question.

## The question

villa's open-problems doc, closing section: *can we reliably tell "no ink" apart from "no ink
recovered yet"?* The instrument was the six released `PHerc.1667-iteration-*` checkpoints, identical
in architecture and step budget and differing only in pseudo-label density. The hypothesis: where
ink is genuinely absent the six agree; where ink is present but unrecovered they disagree.

## What the frozen rules returned

Target `scroll1_20231210121321`, 16384^2 at level 0, predictions at 4096^2, ground truth at its own
resolution.

| | primary [31,-8] | unshifted | wrong-dir [-31,8] |
|---|---:|---:|---:|
| false negatives | 378,691 | 460,085 | 583,874 |
| true negatives | 3,403,773 | 3,322,379 | 3,198,590 |
| **AUC p_std, all six** | **0.5268** | 0.5163 | 0.5062 |
| AUC p_std, ladder it1..5 | 0.4758 | 0.4902 | 0.5003 |
| floor p_mean | 0.5169 | 0.5012 | 0.4970 |
| floor p_max | 0.5072 | 0.5035 | 0.5015 |
| floor permuted | 0.5001 | 0.5002 | 0.5001 |

Powered on every arm. **No signal.** 0.5268 against a permuted floor of 0.5001 is nothing, it is
below the pre-registered 0.55 boundary, and the pure density ladder is **below chance** at 0.4758.
`p_std` exceeds `p_mean` by 0.010, which is not a margin.

The controls behaved: primary beats the wrong-direction arm, so the study is not void by that rule,
and primary and secondary agree on the verdict, so there is no alignment conflict.

## Why this is not an answer

**The instrument is not calibrated.** On this segment the published canon prediction fires on
**14.1%** of pixels. Our six members fire on **59 to 82%**. On the models' own scroll the same
pipeline gives 7.0% against a published 2.8%. It runs hot everywhere and much hotter here.

Saturation compresses the probability range, and a compressed range destroys a disagreement
statistic whether or not the underlying signal exists. So a null `p_std` AUC is exactly what this
pipeline would produce in either world, which makes the measurement uninformative rather than
negative.

Known differences from the published inference recipe, any of which could account for it: the
published runs use `tile256-stride128`, so 2x overlap averaging, where this used stride 256 with no
averaging; they apply a fragment mask and skip windows that touch it, where this scored every tile;
and the model card documents three mutually inconsistent intensity conventions (see
`reports/ink_ablation_scale_bug.md`), of which `clip(0,200)/255` was chosen because it alone lands
near the published rate on the home scroll.

## What is and is not established

**Established:** the released checkpoints load, run, and can be scored end to end against registered
ground truth with no coordinate bridge; the pre-registered rules execute and discriminate; and the
pipeline's absolute calibration is off by 4 to 6x against a published reference on the same data.

**Not established, and not to be reported:** that ablation disagreement fails to separate absence
from failure. That is the hypothesis, it returned a null, and the null is confounded by saturation.

**Explicitly not established:** anything about cross-scroll transfer of these models. That claim was
voided once already today for a different reason and remains untested.

## What would make it a real test

Reproduce the published recipe closely enough that firing rates land near 14% on this segment:
stride-128 overlap averaging, the fragment mask, and whichever intensity convention the canon
pipeline actually uses rather than the one inferred from a card that contradicts itself. Only then
does a null mean something.

The pre-registration, the scorer, and the three alignment arms all survive that change unaltered,
which is the one piece of good news here: the analysis is reusable, and only the input pipeline needs
fixing.
