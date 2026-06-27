# June 2026 Progress Prize — Filing Draft

**Status:** DRAFT for review. Deadline 2026-06-30 11:59pm PT. File via the official Progress Prize form once it opens.
**Repository (the submission artifact):** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)
**Live experiment tracking:** https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

---

## Title

**Vesuvius Autoresearch: open-source tooling and an honest evaluation methodology for autonomous ink-detection research.**

## Summary

A continuously-running, evidence-gated research loop for ink detection on a single consumer GPU (RTX 4090), released open-source with reusable tools and a candid record of what works and what doesn't. The submission is the **toolset and methodology**, not a state-of-the-art detector. Every result is reproducible and tracked.

## What is being released (open tools)

1. **Scroll-specific 3D augmentation library** (`scroll_augmentations.py`) — nine GPU-native augmentations modeling scroll-CT artifacts (beam scatter/decohesion, sheet compression, missing slices, Rician noise, blank dropouts, warping, squeeze, z-dropout, intensity drift). Directly addresses [villa issue #201](https://github.com/ScrollPrize/villa/issues/201). Documented, tested, with a [before/after demo on real scroll patches](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/augmentation_demos/all_families.png). Reusable via a config-free API. → [docs/SCROLL_AUGMENTATIONS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/SCROLL_AUGMENTATIONS.md)

2. **GPU fiber/ridge/vesselness detection** (`vesuvius_autoresearch.fibers`) — a closed-form symmetric-3×3 eigensolver (Cardano) that avoids the cuSolver `eigvalsh` failure on large Hessian batches, with per-array CPU/GPU dispatch and tiled execution for volumes larger than VRAM. Useful for generating fiber/structure labels at scroll scale (cf. [villa issue #193](https://github.com/ScrollPrize/villa/issues/193)). Validated: eigensolver float64 parity 3.1e-10; **14–94× over NumPy** (64³–256³); **512³ tiled in ~3–5 s at ~1 GB VRAM**. Ships a CLI and tests. → [docs/FIBER_DETECTION.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/FIBER_DETECTION.md), [validation report](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/fibers_gpu_validation_2026-06.md). (Proposed upstream as villa PR #1033; the branch and evidence remain public and reproducible.)

3. **Topology-aware evaluation toolkit** — selects the binarization threshold that maximizes centerline overlap and reports the prize topology metrics (`centerline_dice`, `skeleton_distance_length`) there, plus a per-patch discrimination-AUC diagnostic. This surfaced that common ink-detection validation metrics are **artifact-saturated** (see Findings).

4. **The autoresearch loop** (`run_autoresearch_loop.py`) — a bandit samples architecture/loss/augmentation/hyperparameter families, trains each candidate under a fixed wall-clock budget, evaluates on a held-out fragment, and keeps only configurations that improve held-out validation loss (`val_bpb`) — itself subject to the metric caveats in Findings, which is why the evaluation suite below exists. Now with opt-in Weights & Biases tracking (parameter/gradient histograms, per-cycle metrics, prediction images), mirroring villa's setup.

5. **Evaluation & feasibility-probe suite** — the instruments behind the methodological finding, reusable for any ink-detection study: pooled pixel-AUC measurement (`scripts/pixel_auc.py`, the artifact-free metric), an overfit/feasibility probe (`scripts/overfit_probe.py`, "can the model memorize a fixed batch?"), a same-regime learnable-target control (`scripts/control_fulldata_probe.py`, "can the training regime fit *anything*?"), leak-free spatial-split tooling for held-out regions (`scripts/spatial_split_mask.py`, 128 px buffer), and a gated in-training learning-curve hook (`eval_every_steps`). Together these turn "the model is bad" into a falsifiable, attributable diagnosis.

## Findings (the methodological contribution)

The contribution is a disciplined **localization by elimination**: instead of guessing why autonomous ink detection underperforms, the loop's instruments isolate *where* it fails by ruling out one cause at a time. This arc is documented in full at [FINDINGS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/FINDINGS.md); the from-scratch 64 px negative result has a standalone study at [reports/ink_detection_64px_window_study_2026-06.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/ink_detection_64px_window_study_2026-06.md), and the cross-pipeline replication at [reports/gp_winner_repro/](https://github.com/jonmarrs/vesuvius-autoresearch/tree/main/reports/gp_winner_repro).

- **The ink-detection bottleneck is the modeling recipe/stack — not the data, the environment, the compute, or the 0.5 mm / 64 px window.** We established this by elimination across the June arc:
  - *Capacity, pipeline, augmentation, optimization regime — ruled out.* A fresh model memorizes 16 ink patches to pixel AUC 1.0 in 100 steps, and the **identical** training regime fits a synthetic CT-derived target to **0.99** in ~300 steps — yet our from-scratch loop cannot learn ink from a full fragment at 64 px (flat ~0.51 pooled pixel AUC, with or without augmentation, across a 12 h schedule).
  - *Environment and compute — ruled out.* The published 2023 Grand-Prize TimeSformer pipeline reproduces here end-to-end (rendering legible Greek letterforms on canonical Scroll-1 segments) and **retrains from scratch to held-out per-patch AUC 0.905** on real labeled segments, on the single RTX 4090.
  - *Data, labels, and the 64 px window itself — ruled out.* Fed *our exact* Scroll-1 fragments and labels — the very Fr47→Fr143 split our loop uses — that proven recipe reaches held-out AUC **0.711**, where our own loop sits at **~0.56** on the identical data and window.

  What remains is our **model + training stack** (architecture, recipe, through-surface depth context, label cleaning, pretraining). This *supersedes* our own earlier reading that the window was the binding constraint: a prize-compliant 64 px recipe demonstrably extracts real, transferable ink signal — our lightweight from-scratch loop simply doesn't yet. That is a concrete, attributable, fixable target rather than an intrinsic limit. (Full arc: FINDINGS.md "GP-winner replication" Phases 1–4.)
- **Validation metrics are artifact-saturated.** On ink-rich patches (~60% ink), a near-constant predictor scores Dice ≈ 0.75; so Dice/`val_bpb` alone don't prove a model localizes ink. Pooled pixel AUC is the honest signal (0.5 = chance), and it is what exposes the chance-floor result above.
- **A topology "readiness" gate we inherited is provably invalid for ink detection — a second, sharper instance of metrics misleading.** The loop gated submittability on a skeleton-distance metric (`skel_dist ≤ 2.0`) borrowed from villa's *3D fiber/surface* evaluation track. A four-case probe ([scripts/probe_skel_dist_validity.py](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/scripts/probe_skel_dist_validity.py)) shows it is a symmetric-KL divergence between *skeleton branch-length histograms* — blind to spatial location and recall (a prediction shifted **completely off** the label scores 0.0 and passes; 60 % recall passes) and hypersensitive to the fragmentation that thresholding any real probability map produces (a spatially-correct but broken centerline fails by ~20×). It is uncorrelated with detection quality, so *no* model — including the AUC-0.9 TimeSformer above — can pass it. We removed it as a gate; the honest readiness signal is pixel-AUC plus human legibility. (FINDINGS.md "Phase 4b".)
- **Some approaches are architecturally incompatible with the 64 px window** (a practical note, not a claim the window forbids signal): a LeJEPA self-supervised checkpoint loads only ~20% of its encoder at 64 px (it was pretrained large-window), and a clDice late-fine-tune degraded centerline overlap rather than helping.
- **Bugs found and fixed via the rigor.** A Frangi fiber target silently trained on zeros; five of nine sampled augmentations were silent no-ops; the ridge feature channel was silently all-zeros (a cuSolver/backend bug in upstream tooling); a pseudo-label inference path mis-aligned patches by ±32 px until caught in review — all fixed.

## Honest current results

Measured by the artifact-free metric (pooled pixel AUC, 0.5 = chance), our own loop
does not yet have a working detector: from scratch at 64 px it sits at the chance
floor on held-out data (~0.49–0.52), and the production checkpoint reaches only
~0.557 — warm-start accumulation across many cycles, marginally above chance, not a
working detector. We state this plainly: **the contribution is the open tooling and
the localization, not a state-of-the-art model.** Crucially, the gap is now
*attributable* rather than mysterious: a proven recipe extracts AUC 0.711 from the
same window and the same data, so the deficit is concretely our training stack — a
fixable target, not an intrinsic limit. And a careful evaluation overturns optimistic
Dice-based readings (Dice ≈ 0.75 from a near-constant predictor), which is itself part
of the methodological contribution.

## Reproducibility

Public repo, MIT-licensed, with a working quick start (install via `uv sync`, download a fragment, run a smoke test and a cycle), per-tool docs, tests, and a live wandb dashboard. Tools are independently usable:

```bash
# fiber detection on a volume
python -m vesuvius_autoresearch.fibers.cli --input vol.npy --filter vesselness --output ves.npy
# augmentation demo
PYTHONPATH=.:scripts/training uv run python scripts/visualize_scroll_augmentations.py
# tests
PYTHONPATH=.:scripts/training uv run python -m pytest tests/
```

## Community signal

- Technical post in the ScrollPrize Discord `#code` requesting benchmark replication of the GPU fiber detection (see `reports/community_signal_2026-06.md`).
- Public fork branch + reproduction commands for the fibers work.

## Recovery note (context)

Earlier (May) PRs to villa were closed; this submission does not resubmit them as-is. It instead releases the maintained, validated versions in a public, reproducible repo with honest documentation, per the Progress Prize's emphasis on open tools, documentation, and community adoption.

## Links

- Repo: https://github.com/jonmarrs/vesuvius-autoresearch
- Findings: .../blob/main/FINDINGS.md
- 64 px window learnability study: .../blob/main/reports/ink_detection_64px_window_study_2026-06.md
- Augmentations: .../blob/main/docs/SCROLL_AUGMENTATIONS.md
- Fiber detection: .../blob/main/docs/FIBER_DETECTION.md
- wandb: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch
