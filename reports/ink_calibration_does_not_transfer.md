# Ranking transfers across scrolls; calibration does not

**2026-08-30.** Measured on the six released `PHerc.1667-iteration-*` checkpoints, public data
throughout, one consumer GPU.

## The two halves

**Ranking transfers.** Against ScrollGT's registered ground truth on held-out Scroll 1 segment
`20231210121321`, four of six members read ink at AUC 0.68 to 0.72, monotone in pseudo-label
density (it1 0.507, it2 0.532, it3 0.684, it4 0.723, it5 0.725 across 3,396 to 33,061 training
tiles). The published canon prediction scores 0.8243 on the same target, which independently
validates the label.

**Calibration does not.** The same model, same pipeline, same region size, six locations per scroll:

| scroll | it5 fires above 0.5 | range |
|---|---:|---|
| PHerc 1667, the models' **home** scroll | **18.7%** (median) | 3.1 to 26.0% |
| Scroll 1, **held out, different scroll** | **72.5%** (median) | 38.4 to 86.2% |

The ranges do not overlap. The home-scroll figure matches iteration-5's own published held-out
preview, which fires on 26.3%, so the pipeline is right and the shift is real: **3.9x at the median**.

## Why this matters for villa's open problem

The open-problems doc asks whether we can *"reliably tell 'no ink' apart from 'no ink recovered
yet'"*. That is a **threshold** question, and a threshold is exactly what does not survive the
crossing. On a new scroll these models still order pixels correctly, but a fixed 0.5 cut calls most
of the segment ink. An absence determination made that way is a statement about the calibration
shift, not about the papyrus.

This also explains a null we measured separately: disagreement across the ablation series separates
false from true negatives at AUC 0.5268, barely above a permuted floor of 0.5001. The series does not
rescue the threshold, because every member is shifted the same way.

## What would follow, if anyone wants it

The constructive reading is that cross-scroll ink work should use **rank-based** decisions, or
recalibrate per scroll against a small labelled anchor, rather than porting a threshold. A model that
ranks at 0.72 is useful; the same model thresholded at 0.5 on a new scroll is not.

## Limits, plainly

The AUC results cover all six members on one segment. **The firing-rate comparison is it5 only**, six
locations per scroll, one segment each. One architecture, two scrolls, and the Scroll 1 ground truth
carries a stated ~0.31 mm resolution limit, so its scores are mild lower bounds.

Our pipeline deviates from the published inference recipe in that it applies no fragment mask.
Overlap averaging was tested and ruled out as an explanation: stride 128 versus stride 256 moves the
firing rate from 92.9% to 95.1% on a fixed patch, which is nothing.

Everything here is reproducible from `repro/ink_ablation/` and `scripts/run_ink_ablation.py`.
