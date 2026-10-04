# Correction: findings 71–76 re-analysed on villa's supervised region

**2026-10-04.** Result of `docs/preregistration/2026-10-04_supervised_reanalysis.md` (registered `afefc8b3`;
script `scripts/reanalyse_supervised.py`, committed `bdf3095c` before it ran). Data:
`reports/supervised_reanalysis.json`. One further analysis is **post hoc** and labelled as such.

## What was wrong

villa publishes `supervision.zarr` beside each `inklabels.zarr`. On the 8 labelled PHercParis4 segments it
covers **3.4–13.3%** of the canvas and holds **97–100% of all labelled ink** (21–34% ink density inside
it, ~0.01% outside). The labels are annotated only inside it. Findings 71–76, and inkagree ≤ 0.2.2,
evaluated on the whole mesh-valid surface, so real but unannotated ink counted as false positives. That
deflated every AP/AUC (e.g. the rendered prediction's median AP 0.74 on supervised pixels vs ~0.1 before)
and could bias paired comparisons. inkagree 0.3.0 evaluates on the supervised region by default.

## What survives (same arms, parameters and bootstrap; domain = mesh-valid ∩ supervised)

| finding | registered claim | on the supervised region | verdict |
|---|---|---|---|
| 71 | smooth vs linear (rendered prediction): no consistent difference | 1 of 8 resolved; \|ΔAP\| < 0.01 in all 8; median ΔAP ≈ 0 | **survives** |
| 72 | the scorer's label agreement is unchanged by smooth | \|ΔAP\| < 0.01 in 8 of 8 | **survives** |
| 73 | smooth's scorer output is not better on coarse grids | smooth ≥ linear in 3 of 8 | **survives** |
| 73 (secondary) | the raw render is slightly better under smooth on coarse grids | resolved in **8 of 8** (was 6), median **+0.84%** of AP (was ~1–2%) | survives, smaller |
| 74 | the tutorial's step 0.5 is the best of four | beats 0.25 (8 of 8, −6.1%) and 2.0 (8 of 8, −20.4%); **vs 1.0: 4 of 8 resolved, median −1.5% (range −4.8% … +1.4%)** | **does not survive as stated** |
| 75 | source build beats the published image's sampling; a wider band beats both | 1.0 beats 0.5 (8 of 8, **−5.3%**; was −8.3%); 2.0 beats 1.0 (8 of 8, **+8.2%**; was +10.3%) | **survives, smaller** |
| 76 Q2 | the scorer is a coarser instrument (AP ratio rises with dilation) | ratio rises 0.55 → 0.74 | **survives** |
| 76 Q1 | (region-scale tracking: an ambiguous null) | **undetermined**: the registered window rule (≥ 25% of a 2048-px window supervised) finds no windows | — |

**Corrected finding 74:** at the tutorial's settings, step 0.5 beats a thinner band (0.25) and a much
wider one (2.0). Against 1.0 there is no consistent difference. The best band is around 0.5–1.0, not
pinned at 0.5.

## The correction's own predictions

1. "AP rises substantially": **held**.
2. "71 and 72 survive": **held**.
3. "74 and 75 survive": **partly failed** (75 survives; 74 does not as stated).
4. "76 Q1, ρ > 0.3 on supervised pixels": **undetermined** (no qualifying windows under the registered rule).

## Post hoc, not registered: finding 76's question where the labels exist

Using 256-px tiles that are ≥ 50% mesh-valid and supervised (286 tiles across the 8 segments;
`scripts/posthoc_q1_supervised_tiles.py`, `reports/posthoc_q1_supervised_tiles.json`):

| density vs label density, within supervised tiles | Spearman ρ | 95% CI (bootstrap over segments) |
|---|---:|---|
| rendered strip (the scorer's input) | **+0.61** | [+0.42, +0.69] |
| scorer fg density (what `total_fg_pixels` counts) | **+0.15** | [+0.01, +0.21] |

Where villa's labels are defined, the rendered prediction tracks how much ink is labelled, but villa's
scorer count tracks it only weakly. **This is a lead, not a finding.** It was computed after seeing the
registered analysis fail to produce windows, on the same 8 segments. Confirming it needs a pre-registered
test, ideally on labelled segments beyond these 8.

**Follow-up (finding 78, `reports/scorer_tracking_gap.md`):** the registered test held. It mainly shows
robustness to tile size, because the other arms were near-duplicates. Two qualifications:
* the strip may be in-sample for villa's 3D ink model, whose training set is plausibly these 8 segments;
* the scorer's weak ρ is a floor effect: it marks 0.91% of the annotated region, about 2% of labelled ink.

No labelled segments beyond these 8 exist on the current frame.

## What changes elsewhere

* `SPIRAL_FINDINGS_SUMMARY.md`: finding 77 records this correction; finding 74 is marked as corrected.
* The October draft quotes supervised-region numbers and discloses the correction.
* inkagree's README: the correction notice (0.3.0) and the corrected first-use numbers.
* Old numbers stay in the original reports, marked as computed on the unsupervised domain.
