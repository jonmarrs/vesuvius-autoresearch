# PRE-REGISTRATION: can an ablation series tell "no ink" from "no ink recovered yet"?

**Committed UNRUN, 2026-08-30.** The reachability spike is done (`repro/ink_ablation/`), one
checkpoint has been run on 4 tiles to prove it loads, and **no scoring against ground truth has
happened**. Design and decision rules are fixed here first.

## The question, and whose question it is

villa's open-problems doc closes by naming four questions for the 2027 target. One is:

> Can we reduce the dependence on approximate labels, and reliably tell **"no ink" apart from "no ink
> recovered yet"**?

and the ink section carries an explicit open-problem admonition:

> This process helped recover readable text in PHerc. 1667. **But it is not guaranteed to work
> everywhere.** In some scrolls, predictions improve and then plateau. In others, current models show
> little or no convincing ink.

This matters because without it there is no way to know when a scroll is finished, as opposed to
merely not yet read.

## Why this is attackable now

`scrollprize/PHerc.1667-iteration-0` through `-5` were released with **identical architecture and an
identical 12,396-step budget, differing only in pseudo-label density** (`ink0` a cross-segment
baseline, `ink1`..`ink5` increasing label coverage on segment `l_2`). That is a controlled series
someone else built and published, and it is the instrument this study uses.

## The hypothesis

At a location with no ink, all six checkpoints should agree that there is none, and adding
pseudo-label density should not change that. At a location where ink is present but unrecovered, the
series should be **unstable**: some members should fire, or the prediction should move with label
density.

So: **disagreement across the ablation series separates absence from failure.**

## Design

**Data.** ScrollGT target `scroll1_20231210121321`, 4096x4096 at pyramid level 2 of
`2.4um-0.22m-78keV-volume-20260411134726.zarr`, which is the source the target's ground truth was
registered against. Registered ink fraction 0.184. No new coordinate bridge is introduced.

**Held out.** `iteration-0`'s config records training on `500p2a + 658 + 20250910185200 +
20250919125754*`. If any of `iteration-1..5` lists `20231210121321` in `train_segment`, that member
is **excluded and the exclusion reported**, not quietly kept.

**Per pixel** (at the models' native 64x64-per-256x256 output resolution), over all six members:
`p_mean`, `p_max`, `p_std` (the disagreement statistic), and `slope`, the ordinary least squares fit
of probability against ablation index 0..5.

## Decision rules, fixed in advance

Let `N-` be pixels the mean prediction calls negative (`p_mean < 0.5`), split by ground truth into
**true negatives** (GT says no ink) and **false negatives** (GT says ink).

1. **Powered?** If either group has fewer than 1,000 pixels, declare UNPOWERED and report the counts.
2. **The claim:** `p_std` is higher on false negatives than on true negatives. Measured as the AUC of
   `p_std` discriminating the two groups.
   * `AUC >= 0.65` -> the series carries a usable absence-versus-failure signal. Report it.
   * `AUC <= 0.55` -> it does not. Report that as the finding and stop.
   * between -> report the number, draw no verdict.
3. **Floors, published beside the number**, because a score without them means nothing:
   * `p_mean` itself as a discriminator (a confident model may already separate them);
   * `p_max`;
   * a random permutation of `p_std` across pixels, 5 seeds, giving the chance band.
   **If `p_std` does not beat `p_mean`, the ablation series adds nothing over a single model**, and
   that is the honest headline regardless of the absolute AUC.
4. **Slope is reported but is not the claim.** A monotone rise with label density is suggestive and
   is confounded by all five members sharing one training segment.

## What this cannot establish

That the models are right about absence. Ground truth here is a registered human label with a stated
resolution limit of about 0.31 mm; "GT says no ink" means no ink was labelled, not that none exists.
The study measures whether the ablation series *distinguishes* the two label classes, not whether
the labels are complete.

Single scroll, single segment, one architecture, and models trained on a different scroll
(PHerc 1667) applied to Scroll 1, so weak cross-scroll transfer is expected and is part of what is
being characterised rather than a nuisance to be excused.

## Failure modes pre-committed against

* Reporting `p_std` without the `p_mean` floor. Rule 3 makes that the headline.
* Selecting the probability threshold after seeing the split. It is fixed at 0.5.
* Dropping ablation members that behave awkwardly. Only a documented training-segment overlap
  justifies exclusion, and it must be reported.
* Treating a monotone slope as the result. Rule 4 forbids it.
