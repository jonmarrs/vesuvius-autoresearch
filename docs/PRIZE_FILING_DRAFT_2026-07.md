# July 2026 Progress Prize — Filing Draft

**Status:** DRAFT for review. Deadline 2026-07-31 11:59pm PT. Refresh numbers immediately
before filing via the official Progress Prize form. (The June draft was not filed; this
draft supersedes `PRIZE_FILING_DRAFT_2026-06.md`.)
**Repository (the submission artifact):** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)
**Live experiment tracking:** https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

---

## Title

**Vesuvius Autoresearch: rigorous, reproducible measurement of what distillation from the
open SOTA data actually buys — on one consumer GPU, with the honest negative to match.**

## Summary

An open-source research repo (single RTX 4090) that this month rebased onto the newly-open
SOTA data — reproduced the 2023 Grand-Prize detector, distilled it from the released canon
predictions across multiple scrolls, and then **built the ground-truth measurement to check
whether any of it reads real ink** by geometrically registering 2023 hand labels onto the
SOTA re-flattening. The headline contribution is the **measurement discipline and its
finding**, not a strong detector: on a *held-out* segment scored against human labels,
the distilled students read **near chance** (ROC-AUC ~0.55), the released canon prediction
itself scores only **ROC-AUC 0.56–0.70** depending on the segment, and the apparent
distillation "wins" were largely train-region fit. Every metric is defined honestly
(community F1/AP contract; distillation numbers explicitly labeled agreement-with-teacher;
ground-truth numbers gated on validated registration), every result is reproducible from
public data, and — most importantly — the project **caught and corrected its own over-reads**
under review. This is a submission about doing honest science on the frontier data, negatives
included.

## What is being released (open tools)

1. **Ink detector subpackage** (`vesuvius_autoresearch.detector`) — the proven 2023
   Grand-Prize TimeSformer recipe productionized as a tested subpackage
   (`config`/`data`/`model`/`train`/`infer`/`eval`/`cli`) with a one-command `reproduce`.
   Held-out same-scroll: **val_f1 0.393 / AP 0.357 / prevalence-lift 2.07 / ROC-AUC 0.709**
   (proven reference 0.711), window-compliant (64 px lateral; depth is the through-surface
   axis). Surfacing this required fixing real inference defects (input normalization,
   PyTorch-2.6 checkpoint loading, shape alignment) — each documented with a regression
   test. → [reports/detector/REPRODUCTION.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/REPRODUCTION.md)

2. **Community metric contract + cross-fragment measurement** (`detector/metrics.py`,
   `measure` CLI) — `val_f1` (threshold-swept) primary; **average precision** and
   **AP-prevalence-lift** (AP ÷ base rate; ≈1 ⇒ chance) as imbalance-robust honesty gates;
   ROC-AUC demoted to a secondary diagnostic. Includes the **first valid cross-scroll
   measurement** for this project: the same detector scores lift 2.07 same-scroll but only
   **1.29 cross-scroll** — quantifying the generalization gap the field is attacking.
   → [reports/detector/cross_scroll_measurement.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/cross_scroll_measurement.md)

3. **SOTA open-data tooling** (`repro/sota_data/`) — anonymous-S3 discovery/fetch of
   `s3://vesuvius-challenge-open-data/`, OME-Zarr region extraction, detector-format
   conversion with loud alignment guards, and a documented survey of what the bucket
   actually ships (re-flattened multiscale surface volumes + model predictions; **no
   ground-truth ink labels aligned to the new geometry** — a practical fact other teams
   will hit too).

4. **SOTA distillation + ground-truth measurement pipeline** (`repro/sota_data/`) —
   teacher–student distillation from the released canon predictions onto SOTA surface volumes
   (disjoint train/held-out segments, chance-floor baseline, persisted provenance), the
   multi-scroll registry + controlled cross-scroll experiments, **and** the ground-truth
   registration harness (`register.py`, `register_run.py`) that bridges 2023 hand labels onto
   SOTA geometry and scores against them, gated on validated alignment.
   - *Agreement-with-teacher* results (fidelity to the released prediction, NOT accuracy):
     held-out val_f1 0.372 → 0.662 / lift 0.98 → 3.24; multi-scroll diversity lifts unseen-
     scroll transfer 1.22 → 2.12, saturating at ≈2.1 with a third scroll.
   - *Ground-truth* results (vs human labels): the canon teacher scores ROC-AUC 0.56–0.70
     (segment-dependent); on a **held-out** segment the distilled students read **near chance
     (ROC-AUC ~0.55)** — the agreement-with-teacher gains were largely train-region fit.
   → [sota_distill_measurement.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/sota_distill_measurement.md),
   [cross_scroll_scale.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/cross_scroll_scale.md),
   [registered_gt_heldout_validation.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registered_gt_heldout_validation.md)
   → [cross_scroll_distill.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/cross_scroll_distill.md),
   [cross_scroll_scale.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/cross_scroll_scale.md)

5. **Carried forward from June (still maintained):** the scroll-specific 3D augmentation
   library ([villa #201](https://github.com/ScrollPrize/villa/issues/201);
   [docs/SCROLL_AUGMENTATIONS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/SCROLL_AUGMENTATIONS.md)),
   GPU fiber/ridge detection (closed-form 3×3 eigensolver, 14–94× over NumPy;
   [docs/FIBER_DETECTION.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/FIBER_DETECTION.md)),
   the evaluation & feasibility-probe suite (pixel-AUC, overfit probe, learnable-target
   control, leak-free spatial splits), and the autoresearch loop itself.

## Findings (the methodological contribution)

Full narrative: [FINDINGS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/FINDINGS.md).
The through-line is measurement honesty:

- **The metric matters more than the model.** Dice/`val_bpb` saturate on ink-rich patches
  (a near-constant predictor scores Dice ≈ 0.75); ROC-AUC is over-optimistic under class
  imbalance. The adopted contract (F1-swept + AP + prevalence-lift) exposed both our own
  chance-floor results and the real improvements.
- **A "prize topology gate" we inherited is provably invalid** (`skel_dist` is a
  branch-length-histogram divergence, blind to location — a zero-overlap prediction passes).
  We removed it and published the probe.
- **Cross-scroll generalization is the bottleneck, quantified:** lift 2.07 same-scroll →
  1.29 cross-scroll for the same detector; and better data alone does not fix it (the
  detector run on SOTA data produced texture, not ink, until retrained).
- **Distillation reproduces the teacher on consumer hardware — measured as agreement, then
  checked against truth.** Training against the canon predictions lifted held-out
  *agreement-with-teacher* from chance to lift 3.24 (disjoint segments, review-verified). But
  the ground-truth calibration below shows this is teacher *fidelity*, not reading ability:
  on held-out data vs human labels the same students are near chance. Read the 3.24 as
  "faithfully reproduces the teacher," not "reads ink."
- **Training-scroll diversity drives generalization; scaling saturates — both measured.**
  At fixed budget, adding a second training scroll lifted unseen-scroll (PHerc 1667)
  transfer from lift 1.22 to 2.12 (single-scroll distillation actually *over-specializes*,
  landing below the undistilled detector cross-scroll); a third scroll plus 50% more data
  did not lift it further (≈2.1 plateau). A full bucket sweep found only 4 of 45 scrolls
  ship canon teacher predictions today — the practical frontier is released teachers, not
  scan volumes.
- **Negative results, kept honest:** a community-style full-resolution 2.5D ResEncUNet
  *underperformed* the TimeSformer under our recipe (val_f1 0.369 vs 0.393) — the
  architecture likely needs the full nnU-Net protocol; documented rather than discarded.
- **Ground-truth calibration on SOTA data (registered hand labels) — the load-bearing
  finding.** No ground-truth labels aligned to the SOTA re-flattening are released, so we
  built the bridge: register the 2023 hand label onto SOTA geometry via the segment's
  `original.obj` vertex texture coordinates (nearest-vertex map, ~8 old-scan-voxel residual),
  gate on validated alignment before scoring, then measure. Two segments:
  - **A datapoint nobody outside the core team has published:** the released canon prediction
    scores **ROC-AUC 0.56–0.70 vs human labels**, segment-dependent (0.70 on one, 0.56 on
    another where it reads the ink poorly). Agreement-with-teacher was therefore agreement
    with a *variable, often mediocre* proxy — not truth.
  - **The sobering held-out result:** on a segment **no distilled student trained on**, scored
    against human ground truth, the students read **near chance (ROC-AUC ~0.55, prevalence-
    lift ~1.16)** — statistically tied with the (weak) teacher and the undistilled detector.
    The distilled "wins" reported on training regions (up to ROC-AUC 0.80) were **substantially
    train-region fit**. Distillation faithfully reproduces the teacher — *including its
    failures* — rather than learning to read independently. (The same registration quality let
    the good-teacher segment score 0.70, so the near-chance number is real, not a registration
    artifact.)
  - → [registered_gt_validation.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registered_gt_validation.md),
    [registered_gt_heldout_validation.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registered_gt_heldout_validation.md)
- **We caught and corrected our own over-read.** The first (train-region) ground-truth result
  was initially framed as students "matching or exceeding" the teacher; internal review flagged
  a binary-vs-continuous metric confound and the train-region confound, and the held-out
  measurement then showed the effect was largely fit. The committed reports lead with the
  corrected framing. This self-correction *is* the methodological contribution.

## Honest limitations (stated plainly)

- **We do not have a strong ink detector.** On held-out data vs human ground truth the
  distilled models read near chance. The agreement-with-teacher figures (up to lift 3.24)
  measure fidelity to a released model output, not reading ability; where that output is weak,
  matching it is worthless. This is stated so no reader mistakes the distillation numbers for
  accuracy.
- **The ground-truth registration is approximate and one validation used a teacher-free gate.**
  The registration is a nearest-vertex geometric bridge (~8 old-scan-voxel residual); its 2D
  orientation is carried from a decisively-validated segment as an export-pipeline invariant
  (the residual/periodicity checks are convention-blind). On the held-out segment the standard
  (teacher-dependent) alignment gate false-negatived because the teacher is weak there, so
  validation used a codified teacher-free gate (residual + text-line periodicity) — disclosed
  in the report and reproducible from the committed code.
- **The clean cross-scroll ground-truth test is still blocked:** PHerc 1667 (and other
  non-training scrolls) ship only model predictions, no released human labels, so a fully clean
  cross-scroll domain-ceiling measurement isn't yet possible. Re-checkable as the bucket grows.
- The prior distillation held-out region also served as its best-epoch selection set (AP/ROC-AUC
  are threshold-free and unaffected); noted in that report.
- We claim an **honest, reproducible measurement apparatus** on the SOTA data — reproduce the
  reference detector, distill it, and check it against registered ground truth — plus the
  documented finding that distillation-from-canon does not, on this evidence, yield independent
  reading. Not a state-of-the-art model.

## Reproducibility

Public repo, MIT-licensed. The data path uses only the open bucket (anonymous S3, partial
OME-Zarr reads — no credentials, no special hardware beyond one 24 GB GPU):

```bash
# unit tests (CPU)
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py tests/test_sota_*.py -q
# reproduce the working detector (train + eval, GPU)
uv run python -m vesuvius_autoresearch.detector.cli reproduce
# cross-scroll measurement of any checkpoint
uv run python -m vesuvius_autoresearch.detector.cli measure --checkpoint <ckpt>
# SOTA distillation end-to-end (network + GPU)
uv run python -m repro.sota_data.distill_run prep|baseline|train|measure
```

## Links

- Repo: https://github.com/jonmarrs/vesuvius-autoresearch
- Findings: .../blob/main/FINDINGS.md
- Lab notebook: .../blob/main/docs/LAB_NOTEBOOK.md
- Detector reproduction: .../blob/main/reports/detector/REPRODUCTION.md
- Cross-scroll measurement: .../blob/main/reports/detector/cross_scroll_measurement.md
- SOTA distillation result: .../blob/main/reports/detector/sota_distill_measurement.md
- SOTA data survey (qualitative slice): .../blob/main/reports/detector/sota_scroll1_qualitative.md
- wandb: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

## Pre-filing checklist (internal — delete before submission)

- [ ] Refresh all numbers against the latest committed reports (esp. if cross-scroll
      distillation lands before filing).
- [ ] Re-verify every repo link resolves on GitHub main.
- [ ] Confirm no AI-authorship markers anywhere in linked artifacts.
- [ ] File via the official Progress Prize form before 2026-07-31 11:59pm PT.
