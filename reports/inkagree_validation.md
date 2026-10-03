# inkagree reproduces findings 71 and 72 exactly (16/16)

**2026-10-03.** `scripts/validate_inkagree.py` drives inkagree 0.1.0 (local commit `45e3345`, projects/inkagree)
through its library API on the stored inputs of the two registered studies it was built from. It uses the
same parameters and the same random-generator sequence. Expected values are read from
`reports/interp_vs_labels.json` and `reports/scorer_vs_labels.json`, never typed in. Data:
`reports/inkagree_validation.json`.

| study | segments | point estimates (AP, ΔAP, ΔAUC) | bootstrap intervals | exclusions |
|---|---:|---|---|---|
| finding 71 (rendered prediction, level 2) | 8 | identical (tolerance 1e-12) | identical | as registered, except the intended fix below |
| finding 72 (scorer probability, level 3) | 8 | identical | identical | none, as registered |

**The intended difference.** Finding 71 excluded `20230929220926` as "misaligned". In fact its gate
window held no labelled ink, so every AUC was NaN (the defect disclosed in that report). inkagree calls
it **"undetermined"**, and the validator checks for exactly that.

**Found while validating, and fixed before release.** On villa's scorer probability maps, AUC against
the labels is only ~0.57. The alignment surface is flat: the best shift beats (0, 0) by just
0.0004–0.001, and the argmax lands on a corner of the search range. A strict argmax gate therefore
called all 8 segments "misaligned" with no evidence. inkagree now requires an offset to beat (0, 0) by
`min_gain` (default 0.002 AUC) before calling it misaligned, and `--gate-on` lets a weak arm be gated
on the raw render, as finding 72 did. The validator reproduces the original analyses with
`min_gain=0` and their original gate images.

**Default gate on the corpus (descriptive).** With inkagree's defaults (whole-domain gate, ±2 px,
min_gain 0.002) all 8 finding-71 segments align within 1 px (gain ≤ 0.0003) and are compared. This
matches finding 71's post-hoc all-8 sensitivity analysis. Finding 71's central-window gate had seen a
local 3-px offset in `20231012184424` that the whole segment does not have.
