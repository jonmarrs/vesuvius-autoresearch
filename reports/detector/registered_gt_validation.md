# First ground-truth-validated scores on SOTA data (registered label)

**All rows are scored against the REGISTERED hand ground-truth label** (method: obj-exact: original.obj vt (386108 vertices), NN bridge via on-7.91um tifxyz (same old-scan frame), vt convention rowHv_colu (selected by teacher-enrichment among 4 discrete candidates, disclosed; orientation verified visually); region median correspondence residual 7.92 old-scan voxels; registration is approximate. NOTE: the residual measures correspondence SCATTER, not absolute placement -- a label can have a tight residual and still be bodily displaced, which is exactly the 2026-08-07 LEVEL0_SHAPE bug. Scatter depresses rows about equally; a systematic offset does NOT, and can reorder them. Check placement with `scripts/probe_registration_offset.py`, never with the residual alone). The 'canon teacher' row scores the released model prediction itself against human labels.

**Confound 1 (train region):** this region was a TRAINING region for all three distilled students, so their rows are *train-region fit-quality vs ground truth*, NOT held-out generalization. The **unconfounded** rows are the canon teacher and the legacy detector (neither trained here).

The teacher row's label orientation was picked among 4 discrete candidates by teacher-enrichment (decisive here, 5.05 vs 0.90/1.09/1.50); the correspondence geometry and residual are teacher-free, so this is at most marginally optimistic.

**PLACEMENT: 46.6 level-2 px — passes the 48 px gate by only 1.4 px.** Read this row's absolute values with more caution than the held-out target's, which sits at 32.0 px. This segment was *not* affected by the 2026-08-07 `LEVEL0_SHAPE` bug (the hardcoded constant was its own geometry), so its offset is a separate matter: either the cross-scan floor varies more by segment than the held-out measurement suggested, or this target carries an additional defect that has not been isolated. Its excess over the mesh-cell-rounding prediction is a suspiciously uniform ~(-30, -31) px on both axes, which is a lead, not a diagnosis — a same-looking numeric coincidence was chased once already in this investigation and turned out to be nothing. **The threshold was deliberately NOT raised to give this row headroom.** Placement uncertainty here is **~0.45 mm**, vs 0.31 mm on the held-out target; see `MAX_PLACEMENT_OFFSET_L2PX` and `reports/detector/registration_offset_2026-08-07.md`.

**Confound (binary vs continuous):** the teacher is a BINARY map; ROC-AUC and AP reward the ranking that the students' continuous probability maps have and a binary map cannot, so they structurally understate the teacher. The *fair* teacher-vs-student comparison is F1 (`f1_at_0.5`): read the students as matching or modestly exceeding teacher F1, NOT as the larger ROC-AUC/AP gap.

Segment `20230702185753`, level-2 region (4000,2500)+4096.

| model (vs registered ground truth) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| canon teacher (binarized release) | 0.4372 | 0.4372 | 0.2573 | 2.0048 | 0.3643 | 0.5466 | 0.1283 | 0.7031 |
| legacy detector | 0.2275 | 0.1845 | 0.1201 | 0.9359 | 0.1283 | 1.0000 | 0.1283 | 0.4858 |
| arm A (1-scroll student) *(trained on this region)* | 0.4568 | 0.4568 | 0.4096 | 3.1914 | 0.3559 | 0.6375 | 0.1283 | 0.7941 |
| arm B (2-scroll student) *(trained on this region)* | 0.4401 | 0.4401 | 0.3898 | 3.0374 | 0.3558 | 0.5767 | 0.1283 | 0.7807 |
| arm C (3-scroll student) *(trained on this region)* | 0.4675 | 0.4675 | 0.4222 | 3.2898 | 0.3773 | 0.6144 | 0.1283 | 0.7995 |

Overlays: `local_data/sota_registration/orig/overlay_label_on_sota.png`, `overlay_label_on_teacher.png` (git-ignored); committed evidence render: reports/detector/registered_gt_overlay.png.
