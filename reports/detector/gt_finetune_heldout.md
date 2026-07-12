# Ground-truth fine-tuning vs distillation (held-out 20231210121321 GT)

**Before/after fine-tuning the best distilled model (arm C) on human ground-truth labels** registered onto SOTA geometry for 2 Scroll-1 segments (4/4 regions passed the teacher-free alignment gate). All rows scored against the held-out registered ground truth of a segment NO model trained on. POC: only 2 training segments -- a near-chance 'after' is confounded by data thinness, a clear lift is not.

Fine-tune: init arm C `detector_epoch=11.ckpt`, lr 8e-06, 6 epochs, final epoch `ft_epoch=5.ckpt`.

| model (vs held-out GT) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| arm C (distilled, before) | 0.3098 | 0.2304 | 0.2130 | 1.1654 | 0.2045 | 0.6392 | 0.1827 | 0.5576 |
| arm C + GT fine-tune (after) | 0.3090 | 0.1507 | 0.1991 | 1.0898 | 0.1827 | 1.0000 | 0.1827 | 0.5308 |

## Interpretation (negative result)

**GT fine-tuning did not add held-out reading — it subtracted discrimination.**
ROC-AUC fell 0.5576 → 0.5308 and AP-lift 1.165 → 1.090. The after-model's
signature is degenerate: recall 1.000 with precision equal to prevalence
(0.1827), and its threshold-swept F1 (0.3090) equals the trivial all-positive
predictor's F1 at that prevalence (2p/(1+p) = 0.3090) — i.e. six epochs of
fine-tuning on 4 registered-GT regions drove the distilled model toward
predict-everything on the held-out segment rather than toward reading it.

**Scope and confounds, honestly stated:** this is a POC with only 2 training
segments (4 regions). A *lift* here would have been strong evidence; the
observed *absence* of lift is confounded by data thinness, registered-label
noise (correspondence residual ~7.9–8.1 old-scan voxels smears strokes at 64px
scale), and the fixed recipe (lr 8e-6 × 6 epochs, no early stop — the
degenerate endpoint suggests over-fitting the 4 regions). What it does
establish: **registered-GT fine-tuning at this scale is not a cheap unlock** —
the held-out ceiling (~0.55 ROC) survives a first injection of human-label
signal, consistent with the held-out GT finding that no model in this family
independently reads this segment.

## Addendum (2026-07-11): additional training-label confound

A post-hoc 4-candidate orientation probe
([orientation_probe_2026-07-11.md](orientation_probe_2026-07-11.md)) found that segment
`20231005123336` — which supplied **2 of the 4 GT fine-tune training regions** — has an
**unverifiable label orientation**: the canon teacher is chance-quality there (enrichment
≈ 1 for all four UV conventions), and text-line periodicity is flip-invariant, so neither
check can confirm the carried `rowHv_colu` prior. If that prior is wrong on this segment,
half the fine-tune training labels were geometric noise. This does not rescue the negative
(the other half's orientation IS directly validated, probe enrichment 3.13), but it adds a
third disclosed confound alongside data thinness and registration residual.
