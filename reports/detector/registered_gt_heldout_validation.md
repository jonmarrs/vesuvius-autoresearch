# Held-out ground-truth scores on SOTA data (registered label, segment 20231210121321)

**All rows are scored against the REGISTERED hand ground-truth label** (method: obj-exact: original.obj vt (427091 vertices), NN bridge via on-7.91um tifxyz (same old-scan frame), vt convention rowHv_colu (selected by teacher-enrichment among 4 discrete candidates, disclosed; orientation verified visually); region median correspondence residual 7.85 old-scan voxels; registration is approximate -- residual noise depresses every row about equally, so absolute values are conservative and the ranking is the robust signal). The 'canon teacher' row scores the released model prediction itself against human labels.

**Held-out (no train confound):** NO student trained on this segment, so the student rows are genuine *held-out generalization vs ground truth*. arm A used this segment for best-epoch *selection* (agreement-with-teacher), so its row is mildly selection-optimistic; **arms B and C are fully clean held-out** and carry the claim.

**Alignment validated teacher-free (the enrichment gate false-negatived here).** The canon teacher reads THIS segment poorly (scattered, non-letterform), so teacher-enrichment (1.68) is not a valid alignment metric and the enrichment gate fails by design. Registration is validated on the codified teacher-free gate (`gate_mode=teacher_free`): 3D correspondence residual 7.85 old-scan voxels (vs the independently-validated slice-5 registration's 7.92) and registered-label text-line periodicity 0.871 (slice-5 orig computes 0.900 by the same `register.label_line_periodicity`). **Scope of this evidence:** residual, periodicity and the overlay's crisp letterforms are *convention-blind* -- they confirm real text landed on the correct 3D manifold, but NOT the 2D orientation. The `rowHv_colu` orientation is carried from slice 5 as an export-pipeline invariant (same scroll/scan/tooling), weakly corroborated here by enrichment 1.68>1 and teacher AP-lift 1.15>1 (a mirrored convention would give ≈1.0). That the teacher is weak here is itself a finding: agreement-with-teacher would reward reproducing this segment's noise, so a held-out ground-truth score measures real reading, not mimicry.

**Metric note (everything reads near chance here):** at this region's ink prevalence (~0.18) the trivial all-positive predictor already scores F1 ≈ 0.31 -- the legacy detector predicts all-positive and sits exactly there -- so `val_f1`/F1 is degenerate and the binary-teacher caveat does NOT rescue the teacher. The robust reads are AP-prevalence-lift and ROC-AUC: teacher 1.15/0.563, arms B/C 1.16-1.17/0.55-0.56, legacy 1.00/0.50 -- all ≈ chance. At `f1_at_0.5` the students actually TRAIL the teacher (0.23-0.26 vs 0.295).

Segment `20231210121321`, level-2 region (4000,2500)+4096.

| model (vs registered ground truth) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| canon teacher (binarized release) | 0.2950 | 0.2950 | 0.2102 | 1.1501 | 0.2653 | 0.3322 | 0.1827 | 0.5632 |
| legacy detector | 0.3090 | 0.2668 | 0.1837 | 1.0052 | 0.1827 | 1.0000 | 0.1827 | 0.5006 |
| arm A (1-scroll student) *(selection-only; not trained here)* | 0.3107 | 0.2578 | 0.2198 | 1.2027 | 0.2003 | 0.6930 | 0.1827 | 0.5626 |
| arm B (2-scroll student) | 0.3107 | 0.2431 | 0.2121 | 1.1609 | 0.1951 | 0.7627 | 0.1827 | 0.5531 |
| arm C (3-scroll student) | 0.3098 | 0.2304 | 0.2130 | 1.1654 | 0.2045 | 0.6392 | 0.1827 | 0.5576 |

Overlays: `local_data/sota_registration/heldout/overlay_label_on_sota.png`, `overlay_label_on_teacher.png` (git-ignored); committed evidence render: reports/detector/registered_gt_heldout_overlay.png.
