# Ranking transfers across scrolls; calibration does not

> ## ⚠ NARROWED TWICE, 2026-08-30: it is Scroll 1, not "crossing scrolls" and not one segment
>
> The title's general claim is **not supported**. Two follow-up tests, in order:
>
> **A third scroll does not show the effect.** On PHerc 0139, at the models' native 2.399 um, the
> shift is **0.86x (it3)** and **0.52x (it5)**: they fire at or BELOW their home rate.
>
> **Three Scroll 1 segments all do show it**, including a 2026 re-segmentation of the same sheet as
> one of the 2023-era ones, all rendered from the *same* 2.4 um CT volume (it5, median of six
> 1024^2 regions):
>
> | segment | vintage | it5 fires above 0.5 |
> |---|---|---:|
> | PHerc1667 `w011` (home) | - | 0.1867 |
> | `20231210121321` | 2023 | 0.7253 |
> | `20230702185753` | 2023 | 0.7129 |
> | `...-20230702185753_v14` | **2026 re-seg** | 0.6670 |
>
> So the effect is **not** segmentation vintage (the 2026 re-seg of the same sheet behaves like the
> 2023 ones), **not** one anomalous segment (three segments agree), and **not** general to crossing
> scrolls (PHerc 0139 does not show it).
>
> **What it is:** these models are out of distribution on **Scroll 1**, firing at roughly 3.6x to
> 3.9x their home rate there while behaving normally on another non-home scroll.
>
> **A candidate mechanism, untested:** PHerc 1667 and PHerc 0139 both publish their surface volumes
> as `2.399um-0.22m-78keV`, while Scroll 1's is `2.4um-0.22m-78keV`, a different reconstruction. The
> effect may track the volume rather than the scroll. Distinguishing those would need a second
> non-home scroll sharing Scroll 1's reconstruction, or Scroll 1 data under the 2.399 um pipeline.
>
> **Unaffected by any of this:** the ranking result, which is measured against ground truth. Four of
> six members read `20231210121321` at AUC 0.68 to 0.72, monotone in pseudo-label density.

## The two halves

**Ranking transfers.** Against ScrollGT's registered ground truth on held-out Scroll 1 segment
`20231210121321`, four of six members read ink at AUC 0.68 to 0.72, monotone in pseudo-label
density (it1 0.507, it2 0.532, it3 0.684, it4 0.723, it5 0.725 across 3,396 to 33,061 training
tiles). The published canon prediction scores 0.8243 on the same target, which independently
validates the label.

**Calibration does not.** The same model, same pipeline, same region size, six locations per scroll:

Medians over six 1024^2 regions per scroll, **all six members**:

| member | home (PHerc 1667) | held out (Scroll 1) | shift |
|---|---:|---:|---:|
| it0 | 0.0800 | 0.5934 | 7.42x |
| it1 | 0.1244 | 0.7412 | 5.96x |
| it2 | 0.2708 | 0.8843 | 3.27x |
| it3 | 0.2053 | 0.6775 | 3.30x |
| it4 | 0.1447 | 0.5848 | 4.04x |
| it5 | 0.1867 | 0.7253 | 3.89x |

Home rates span 8.0 to 27.1%, held-out rates 58.5 to 88.4%. **The two do not overlap for any
member**, and every member shifts the same direction by 3.3x to 7.4x.

Each member's home rate is checked against **its own** published `preview_l_5` figure (it1 0.2763,
it2 0.3649, it3 0.2427, it4 0.2134, it5 0.2627), not against a single number; the previews are on
segment `l_5` while the home leg measures `w011`, so a ratio tolerance is used rather than an
absolute one. it0 is a cross-segment baseline and ships no `l_5` preview, so its home leg is
reported as unvalidated.

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

The AUC results and the firing-rate comparison both cover all six members, six locations per scroll,
one segment per scroll. One architecture, two scrolls, and the Scroll 1 ground truth
carries a stated ~0.31 mm resolution limit, so its scores are mild lower bounds.

Our pipeline deviates from the published inference recipe in that it applies no fragment mask.
Overlap averaging was tested and ruled out as an explanation: stride 128 versus stride 256 moves the
firing rate from 92.9% to 95.1% on a fixed patch, which is nothing.

Everything here is reproducible from `repro/ink_ablation/` and `scripts/run_ink_ablation.py`.
