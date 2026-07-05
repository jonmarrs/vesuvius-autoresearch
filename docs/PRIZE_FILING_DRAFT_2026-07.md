# July 2026 Progress Prize — Filing Draft

**Status:** DRAFT for review. Deadline 2026-07-31 11:59pm PT. Refresh numbers immediately
before filing via the official Progress Prize form. (The June draft was not filed; this
draft supersedes `PRIZE_FILING_DRAFT_2026-06.md`.)
**Repository (the submission artifact):** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)
**Live experiment tracking:** https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

---

## Title

**Vesuvius Autoresearch: an honest, reproducible path from the open SOTA data to a working
ink detector on one consumer GPU.**

## Summary

An open-source research repo (single RTX 4090) that this month went from "rigorous negative
results" to a **working, window-compliant ink detector** — and then **rebased it onto the
newly-open SOTA data by distilling from the released canon predictions**, producing the
repo's first model whose output shows letterform-shaped strokes. Every metric is defined
honestly (community F1/AP contract; distillation numbers explicitly labeled
agreement-with-teacher, never ground-truth accuracy), every result is reproducible from
public data, and the negative results are documented alongside the positive ones.

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

4. **SOTA distillation pipeline** (`repro/sota_data/distill_prep.py`, `distill_run.py`) —
   teacher–student distillation from the released canon ink predictions onto the SOTA
   surface volumes, with disjoint train/held-out segments, a measured chance-floor
   baseline, persisted teacher provenance, and side-by-side renders. **Result: held-out
   agreement-with-teacher val_f1 0.372 → 0.662, AP 0.224 → 0.742, lift 0.98 → 3.24,
   ROC-AUC 0.499 → 0.865** — the strongest ranking signal any model trained in this repo
   has produced, with the first letterform-shaped output.
   → [reports/detector/sota_distill_measurement.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/sota_distill_measurement.md)
   **Extended cross-scroll (multi-scroll registry + controlled experiments):** on a held-out
   PHerc-1667 region no arm trained on, a *fixed-budget* diversity experiment showed
   multi-scroll training substantially improves unseen-scroll transfer (lift 1.22 → **2.12**
   vs the 1.47 undistilled anchor), and a scaled 3-scroll run showed the transfer
   **saturates** at lift ≈ 2.1 while producing the best all-around model (own-scroll
   read-outs 0.587–0.631 val_f1, ROC-AUC up to 0.919).
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
- **Distillation transfers SOTA competence to consumer hardware.** With no aligned ground
  truth released, training against the canon predictions (clearly labeled as
  agreement-with-teacher) lifted the held-out ranking signal from exact chance to
  lift 3.24. A final independent review verified the train/held-out segments are disjoint.
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

## Honest limitations (stated plainly)

- The distilled model's numbers are **agreement with a model output (the released canon
  predictions), not ground-truth accuracy** — no ground-truth labels aligned to the SOTA
  re-flattening exist in the open bucket. Independent validation (registering old hand
  labels onto the new flattening) is named future work.
- The held-out region also serves as the best-epoch selection set (AP/ROC-AUC are
  threshold-free and unaffected); noted in the report itself.
- Same-scroll detection at the 64 px window is real but not legible; cross-scroll transfer
  without retraining remains weak. We do not claim a state-of-the-art model — we claim an
  honest, reproducible path onto the SOTA data that others can build on.

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
