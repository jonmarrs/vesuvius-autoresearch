# Pre-registration: re-analysing findings 71–76 on villa's supervised region (a correction)

**Written 2026-10-04, before any comparison was recomputed on the supervised region.** Script
`scripts/reanalyse_supervised.py`, committed with this file.

## The flaw being corrected

villa publishes a `supervision.zarr` beside each `inklabels.zarr`. On all 8 labelled segments:
* it covers only **3.4–13.3%** of the canvas;
* **97–100% of all labelled ink lies inside it**, at 21–34% ink density there against ~0.01% outside.

The labels are therefore defined only inside the supervised region. Outside it, "no label" means "not
annotated", not "no ink". Every label-anchored analysis in findings 71–76, and inkagree ≤ 0.2.2,
evaluated on the whole mesh-valid domain. It treated unannotated pixels as true negatives, so:
* absolute AP/AUC were deflated;
* paired comparisons could penalise whichever arm finds more real ink in unannotated areas;
* finding 76's region-scale null may simply be supervision coverage.

## Method

For every comparison in findings 71, 72, 73, 74, 75 and 76: the **same stored arms, labels, parameters,
gate and bootstrap**, with one change. The domain becomes **mesh-valid ∩ supervised**, using the
supervision raster at the same pyramid level as the labels (`supervision.zarr/<level>`, > 127). The gate
uses inkagree's defaults (whole domain, ±2 px, min_gain 0.002) for every finding. That is finding 71's
own post-hoc sensitivity choice, and it avoids the central-window artefact.

**A finding "survives" if its registered verdict is unchanged** on the supervised domain:
* 71: no consistent difference;
* 72: P2, scorer faithfulness unchanged;
* 73: P2, smooth's scorer output not better; and the secondary raw-render result;
* 74: 0.5 best;
* 75: 1.0 beats 0.5, and 2.0 beats 1.0;
* 76 Q2: the ratio rises.

Finding 76 Q1 is re-asked on supervised pixels only, using windows with ≥ 25% of the domain supervised.
Count-sensitivity results (findings 70, 72 P1 and 73 P1) do not involve the labels and are not
recomputed.

## Predictions, fixed now

1. Absolute AP rises substantially on the supervised domain, for every arm. Confidence high.
2. Findings 71 and 72 (no difference, unchanged faithfulness) survive. Confidence moderate.
3. Findings 74 and 75 (the band-width directions) survive. Confidence moderate.
4. Finding 76 Q1 changes: on supervised pixels, scorer density tracks label density with ρ > 0.3.
   Confidence low.

## Reporting

A corrections note at the head of each affected report, and in `SPIRAL_FINDINGS_SUMMARY.md` and the
October draft. Old numbers stay, marked as computed on the unsupervised domain. inkagree gets
supervision-aware evaluation as its default (0.3.0).
