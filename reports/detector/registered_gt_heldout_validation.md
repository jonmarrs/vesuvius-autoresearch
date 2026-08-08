# Held-out ground-truth scores on SOTA data (registered label, segment 20231210121321)

**All rows are scored against the REGISTERED hand ground-truth label** (method: obj-exact: original.obj vt (427091 vertices), NN bridge via on-7.91um tifxyz (same old-scan frame), vt convention rowHv_colu (selected by teacher-enrichment among 4 discrete candidates, disclosed; orientation verified visually); region median correspondence residual 7.95 old-scan voxels; registration is approximate. NOTE: the residual measures correspondence SCATTER, not absolute placement -- a label can have a tight residual and still be bodily displaced, which is exactly the 2026-08-07 LEVEL0_SHAPE bug. Scatter depresses rows about equally; a systematic offset does NOT, and can reorder them. Check placement with `scripts/probe_registration_offset.py`, never with the residual alone). The 'canon teacher' row scores the released model prediction itself against human labels.

**Held-out (no train confound):** NO student trained on this segment, so the student rows are genuine *held-out generalization vs ground truth*. arm A used this segment for best-epoch *selection* (agreement-with-teacher), so its row is mildly selection-optimistic; **arms B and C are fully clean held-out** and carry the claim.

**⚠ These numbers REPLACE the 2026-07-07 version of this report, which was invalid.** That run used a hardcoded `LEVEL0_SHAPE` belonging to segment 20230702185753, so this segment's region crop was scaled wrongly and the registered label came out displaced and stretched (x +9.8%, y +0.79%). It produced the since-retracted claim that everything reads at chance here. Fixed 2026-08-07 (`LEVEL0_SHAPES` is now per-segment and `_set_target` refuses an unrecorded segment); see `reports/detector/registration_offset_2026-08-07.md`.

**The enrichment gate was RIGHT and we overrode it.** The 2026-07-07 run read teacher-enrichment 1.68, failed the enrichment gate, and we explained that away as 'the canon teacher reads this segment poorly' -- then built a teacher-free gate to get past it. The gate was not false-negativing: it was correctly detecting the broken registration. On the fixed pipeline the SAME convention scores **enrichment 6.01** (vs 1.77/1.84/1.61 for the alternatives -- now decisive, where before it was marginal), comfortably clearing the gate it previously failed. The teacher-free gate is retained because teacher-independence is genuinely better methodology, not because enrichment cannot be used here.

Registration is validated on the codified teacher-free gate (`gate_mode=teacher_free`): 3D correspondence residual 7.95 old-scan voxels and registered-label text-line periodicity 0.867. **Scope of this evidence:** residual and periodicity are *convention-blind* -- they confirm real text landed on the correct 3D manifold, not the 2D orientation; the `rowHv_colu` orientation is now independently corroborated by the decisive enrichment margin above.

**PLACEMENT UNCERTAINTY — a published spec of this target, not a caveat.** Agreement with the canon prediction peaks at (dy=31, dx=-8) level-2 px, i.e. **32 px ≈ 128 level-0 voxels ≈ 0.31 mm** off zero. That is the resolution limit of this target: features closer together than ~0.31 mm cannot be scored reliably against it, and all absolute values are mild lower bounds.

It is a **floor of the method, not an outstanding bug.** `original.obj` (which carries the vt → 2023 label mapping) lives in the old 7.91 µm scan frame, so reaching a 2023 label from a 2.4 µm-volume position must cross scan frames — and the 2023 and 2026 *segmentations of this sheet are materially different surfaces*. An unpaired 3D similarity between the two meshes fits at scale 0.30466 (vs 0.30341 implied, so the fit is sane) but leaves a broad, non-bimodal residual: p5 7.4, p50 64.4, p90 249.2 old-scan voxels. No rigid transform bridges them tightly, and routing through one would be *worse* than the current mapping (81 old-vx vs ~39). Two candidate fixes were tested and falsified: a domain-vs-label UV flip (enrichment 6.00 vs 6.75), and cropping on the 2.4 µm grid while reading old-frame xyz at the same normalised UV (the two grids do not share a UV domain — 4.6% of extent).

The placement gate is set at 48 px, derived from this floor and ~9× below the 435 px `LEVEL0_SHAPE` bug it is there to catch. See `MAX_PLACEMENT_OFFSET_L2PX` and `reports/detector/registration_offset_2026-08-07.md`.

**Metric note:** at this region's ink prevalence (~0.18) the trivial all-positive predictor scores F1 ≈ 0.31 -- the legacy detector predicts all-positive and sits exactly there, which is the floor to compare against. The robust reads are AP-prevalence-lift and ROC-AUC. The canon teacher is a BINARY map, so ROC-AUC and AP structurally understate it relative to the students' continuous probability maps; the fair teacher-vs-student comparison is `f1_at_0.5`.

Segment `20231210121321`, level-2 region (4000,2500)+4096.

| model (vs registered ground truth) | val_f1 | f1_at_0.5 | average_precision | ap_prevalence_lift | precision | recall | positive_rate | roc_auc |
|---|---|---|---|---|---|---|---|---|
| canon teacher (binarized release) | 0.5718 | 0.5718 | 0.3970 | 2.1542 | 0.5162 | 0.6408 | 0.1843 | 0.7526 |
| legacy detector | 0.3112 | 0.2794 | 0.1859 | 1.0086 | 0.1843 | 1.0000 | 0.1843 | 0.5176 |
| arm A (1-scroll student) *(selection-only; not trained here)* | 0.5014 | 0.5013 | 0.4924 | 2.6716 | 0.4508 | 0.5648 | 0.1843 | 0.7716 |
| arm B (2-scroll student) | 0.4404 | 0.4375 | 0.4309 | 2.3382 | 0.3762 | 0.5309 | 0.1843 | 0.7305 |
| arm C (3-scroll student) | 0.4656 | 0.4549 | 0.4496 | 2.4397 | 0.4076 | 0.5428 | 0.1843 | 0.7462 |

Overlays: `local_data/sota_registration/heldout/overlay_label_on_sota.png`, `overlay_label_on_teacher.png` (git-ignored); committed evidence render: reports/detector/registered_gt_heldout_overlay.png.
