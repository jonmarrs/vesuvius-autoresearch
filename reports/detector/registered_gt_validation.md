# First ground-truth-validated scores on SOTA data (registered label)

> ## ⚠ QUALIFIED — 2026-08-07
>
> This region's registered label is also displaced, though far less than the held-out
> segment's: the GT-vs-teacher agreement peak sits at (dy=−18, dx=−44) level-2 px
> (~190 level-0 voxels), where Dice rises 0.453 → 0.603 and the canon teacher's roc_auc
> rises 0.724 → 0.838. Absolute values here are depressed and the near-parity
> teacher-vs-student reading should be re-derived after root-cause.
>
> Critically, the offsets are **per-segment** (~190 vx here vs ~1766 vx on
> 20231210121321). The filing used this segment's healthy 0.70 to argue the held-out
> near-chance result was "not a registration artifact" — that inference is invalid.
> → [registration_offset_2026-08-07.md](registration_offset_2026-08-07.md)

**All rows are scored against the REGISTERED hand ground-truth label** (method: obj-exact: original.obj vt (386108 vertices), NN bridge via on-7.91um tifxyz (same old-scan frame), vt convention rowHv_colu (selected by teacher-enrichment among 4 discrete candidates, disclosed; orientation verified visually); region median correspondence residual 7.92 old-scan voxels, teacher-enrichment 5.05; registration is approximate -- residual noise depresses every row about equally, so absolute values are conservative and the ranking is the robust signal). The 'canon teacher' row scores the released model prediction itself against human labels -- the first ground-truth calibration of the canon prediction. (The teacher row's label ORIENTATION was picked among 4 discrete candidates by teacher-enrichment, so it is not 100% teacher-independent; the margin was decisive -- 5.05 vs 0.90/1.09/1.50 -- and the correspondence geometry and residual are teacher-free, so this is at most marginally optimistic.)

**Confound 1 (train region):** this region was a TRAINING region for all three distilled students, so their rows are *train-region fit-quality vs ground truth*, NOT held-out generalization. The **unconfounded** rows are the canon teacher and the legacy detector (neither trained here).

**Confound 2 (binary vs continuous):** the teacher is a BINARY map; ROC-AUC and AP reward the ranking that the students' continuous probability maps have and a binary map cannot, so they structurally understate the teacher. The *fair* teacher-vs-student comparison is F1: teacher 0.437 vs students 0.44-0.47 -- near parity. So read the students as: distillation roughly matches teacher fidelity on supervised data (with a modest ranking-quality gain), resolving the saturation question in the teacher-ceiling direction (students are not capped BELOW the teacher where they have supervision) -- NOT as a large accuracy gain over the teacher.

Segment `20230702185753`, level-2 region (4000,2500)+4096.

| model (vs registered ground truth) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| canon teacher (binarized release) | 0.4372 | 0.4372 | 0.2573 | 2.0048 | 0.3643 | 0.5466 | 0.1283 | 0.7031 |
| legacy detector | 0.2275 | 0.1845 | 0.1201 | 0.9359 | 0.1283 | 1.0000 | 0.1283 | 0.4858 |
| arm A (1-scroll student) *(trained on this region)* | 0.4568 | 0.4568 | 0.4096 | 3.1914 | 0.3559 | 0.6375 | 0.1283 | 0.7941 |
| arm B (2-scroll student) *(trained on this region)* | 0.4401 | 0.4401 | 0.3898 | 3.0374 | 0.3558 | 0.5767 | 0.1283 | 0.7807 |
| arm C (3-scroll student) *(trained on this region)* | 0.4675 | 0.4675 | 0.4222 | 3.2898 | 0.3773 | 0.6144 | 0.1283 | 0.7995 |

Overlays: local_data/sota_registration/overlay_label_on_sota.png, overlay_label_on_teacher.png (git-ignored); committed evidence render: reports/detector/registered_gt_overlay.png.
