> **⚠ RETRACTED — 2026-08-15. Do not cite the result below.** Both of this report's
> load-bearing claims are withdrawn, and neither number in the table is interpretable.
>
> * **The headline — "GT fine-tuning did not add held-out reading — it subtracted
>   discrimination" — is retracted.** The model was fine-tuned on a displaced label and
>   scored against a displaced label. A hardcoded `LEVEL0_SHAPE` applied one segment's
>   geometry to every segment (found 2026-08-07); a second copy of the same constant in
>   `gt_register.py` (found 2026-08-14) put the *training* labels in the same condition, two
>   of the four regions carrying a 167% x-scale error. A model scored against a displaced
>   label degrades toward the trivial all-positive predictor — which is precisely the
>   "degenerate signature" this report read as a finding. Post-correction the bar this
>   experiment was posed against, arm C at ROC-AUC 0.558, reads **~0.746**: the distilled
>   models were already reading held-out ink.
>   ([`registration_offset_2026-08-07.md`](registration_offset_2026-08-07.md), resolution
>   box and `:218-235`.)
> * **"4/4 regions passed the teacher-free alignment gate" is retracted.** That gate tested
>   residual and label-line periodicity; it never tested *placement*, which is how this
>   shipped. Under the 2026-08-14 placement gate three of the four regions fail (53.3 px and
>   57.5 px against a 48 px threshold, plus one that drops at prep on periodicity 0.556 /
>   registered ink fraction 0.0005), and the fourth clears by 1.4 px on the segment retired
>   non-scoring the same day. The four `passed: true` records are void wherever they appear,
>   including in this report's companion
>   [`gt_finetune_heldout.json`](gt_finetune_heldout.json), which carries a copy of them.
> * **The 2026-07-11 orientation addendum below is retired** for a different reason — see the
>   note at the end of this file.
>
> **Replacement finding:**
> [`gt_training_data_exhaustion_2026-08-15.md`](gt_training_data_exhaustion_2026-08-15.md).
> The experiment is not merely wrong, it is **not testable**: exactly one Scroll-1 segment is
> hand-labelled, re-flattened and correctly placed, and it is spent as the held-out
> evaluation target. There is no training set to re-run this with, and no amount of compute
> makes one.
>
> Nothing below is deleted. The original text is kept intact so what was published stays
> auditable, per this project's convention for corrections.

# Ground-truth fine-tuning vs distillation (held-out 20231210121321 GT)

**Before/after fine-tuning the best distilled model (arm C) on human ground-truth labels** registered onto SOTA geometry for 2 Scroll-1 segments (4/4 regions passed the teacher-free alignment gate). All rows scored against the held-out registered ground truth of a segment NO model trained on. POC: only 2 training segments -- a near-chance 'after' is confounded by data thinness, a clear lift is not.

> **⚠ RETRACTED (see banner).** "4/4 regions passed the teacher-free alignment gate" is
> void: that gate never tested placement. Three of the four regions fail the 2026-08-14
> placement gate and the fourth sits on a retired non-scoring segment.

Fine-tune: init arm C `detector_epoch=11.ckpt`, lr 8e-06, 6 epochs, final epoch `ft_epoch=5.ckpt`.

| model (vs held-out GT) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| arm C (distilled, before) | 0.3098 | 0.2304 | 0.2130 | 1.1654 | 0.2045 | 0.6392 | 0.1827 | 0.5576 |
| arm C + GT fine-tune (after) | 0.3090 | 0.1507 | 0.1991 | 1.0898 | 0.1827 | 1.0000 | 0.1827 | 0.5308 |

## Interpretation (negative result) — ⚠ RETRACTED 2026-08-15

> **⚠ RETRACTED (see banner).** Both rows of the table above were scored against a displaced
> held-out label, and the "after" model was itself fine-tuned on displaced training labels.
> The degenerate all-positive signature described below is the expected behaviour of a model
> measured against a mislocated target, not evidence about ground-truth supervision. The
> replacement finding is
> [`gt_training_data_exhaustion_2026-08-15.md`](gt_training_data_exhaustion_2026-08-15.md).

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

## Addendum (2026-07-11): additional training-label confound — ⚠ RETIRED 2026-08-15

> **⚠ RETIRED 2026-08-15.** The premise of this addendum is now known to be false. The canon
> teacher was not chance-quality on `20231005123336`; the enrichment collapse (≈ 1 across all
> four orientation candidates) was our own second hardcoded level-0 shape — that segment's
> true level-0 is 34880×97280 against the assumed 50600×36400, a 167% x-scale error that
> scattered the label, and a scattered label enriches at ≈ 1 against any teacher.
> Re-registered with the fix, teacher-enrichment is **4.88** and the orientation is decisively
> determined. So the labels were fine and the registration was broken: this is not a "third
> disclosed confound" on top of a standing negative, it is one more symptom of the defect that
> retracted the negative outright
> (`registration_offset_2026-08-07.md:257-271`;
> [`gt_training_data_exhaustion_2026-08-15.md`](gt_training_data_exhaustion_2026-08-15.md)`:283-301`).

A post-hoc 4-candidate orientation probe
([orientation_probe_2026-07-11.md](orientation_probe_2026-07-11.md)) found that segment
`20231005123336` — which supplied **2 of the 4 GT fine-tune training regions** — has an
**unverifiable label orientation**: the canon teacher is chance-quality there (enrichment
≈ 1 for all four UV conventions), and text-line periodicity is flip-invariant, so neither
check can confirm the carried `rowHv_colu` prior. If that prior is wrong on this segment,
half the fine-tune training labels were geometric noise. This does not rescue the negative
(the other half's orientation IS directly validated, probe enrichment 3.13), but it adds a
third disclosed confound alongside data thinness and registration residual.
