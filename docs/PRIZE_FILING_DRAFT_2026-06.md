# June 2026 Progress Prize — Filing Draft

**Status:** DRAFT for review. Deadline 2026-06-30 11:59pm PT. File via the official Progress Prize form once it opens.
**Repository (the submission artifact):** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)
**Live experiment tracking:** https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

> Internal notes for filing (delete before submission): no AI-authorship markers anywhere. Lead with the open-source tools and the honest methodology, not the model's accuracy. Cite the public fork branch for the fibers work; do not present the closed May/June villa PRs (incl. #1033, closed) as merged or open. Numbers below trace to the committed `FINDINGS.md` and the 2026-06 experiment arc (see `reports/ink_detection_64px_window_study_2026-06.md`) — re-skim them against `FINDINGS.md` at file time in case the loop has logged new figures.

---

## Title

**Vesuvius Autoresearch: open-source tooling and an honest evaluation methodology for autonomous ink-detection research.**

## Summary

A continuously-running, evidence-gated research loop for ink detection on a single consumer GPU (RTX 4090), released open-source with reusable tools and a candid record of what works and what doesn't. The submission is the **toolset and methodology**, not a state-of-the-art detector. Every result is reproducible and tracked.

## What is being released (open tools)

1. **Scroll-specific 3D augmentation library** (`scroll_augmentations.py`) — nine GPU-native augmentations modeling scroll-CT artifacts (beam scatter/decohesion, sheet compression, missing slices, Rician noise, blank dropouts, warping, squeeze, z-dropout, intensity drift). Directly addresses [villa issue #201](https://github.com/ScrollPrize/villa/issues/201). Documented, tested, with a [before/after demo on real scroll patches](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/augmentation_demos/all_families.png). Reusable via a config-free API. → [docs/SCROLL_AUGMENTATIONS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/SCROLL_AUGMENTATIONS.md)

2. **GPU fiber/ridge/vesselness detection** (`vesuvius_autoresearch.fibers`) — a closed-form symmetric-3×3 eigensolver (Cardano) that avoids the cuSolver `eigvalsh` failure on large Hessian batches, with per-array CPU/GPU dispatch and tiled execution for volumes larger than VRAM. Useful for generating fiber/structure labels at scroll scale (cf. [villa issue #193](https://github.com/ScrollPrize/villa/issues/193)). Validated: eigensolver float64 parity 3.1e-10; **14–94× over NumPy** (64³–256³); **512³ tiled in ~3–5 s at ~1 GB VRAM**. Ships a CLI and tests. → [docs/FIBER_DETECTION.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/FIBER_DETECTION.md), [validation report](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/fibers_gpu_validation_2026-06.md). (Proposed upstream as villa PR #1033; the branch and evidence remain public and reproducible.)

3. **Topology-aware evaluation toolkit** — selects the binarization threshold that maximizes centerline overlap and reports the prize topology metrics (`centerline_dice`, `skeleton_distance_length`) there, plus a per-patch discrimination-AUC diagnostic. This surfaced that common ink-detection validation metrics are **artifact-saturated** (see Findings).

4. **The autoresearch loop** (`run_autoresearch_loop.py`) — a bandit samples architecture/loss/augmentation/hyperparameter families, trains each candidate under a fixed wall-clock budget, evaluates on a held-out fragment, and promotes only topology-improving configurations. Now with opt-in Weights & Biases tracking (parameter/gradient histograms, per-cycle metrics, prediction images), mirroring villa's setup.

5. **Evaluation & feasibility-probe suite** — the instruments behind the methodological finding, reusable for any ink-detection study: pooled pixel-AUC measurement (`scripts/pixel_auc.py`, the artifact-free metric), an overfit/feasibility probe (`scripts/overfit_probe.py`, "can the model memorize a fixed batch?"), a same-regime learnable-target control (`scripts/control_fulldata_probe.py`, "can the training regime fit *anything*?"), leak-free spatial-split tooling for held-out regions (`scripts/spatial_split_mask.py`, 128 px buffer), and a gated in-training learning-curve hook (`eval_every_steps`). Together these turn "the model is bad" into a falsifiable, attributable diagnosis.

## Findings (the methodological contribution)

Documented in full at [FINDINGS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/FINDINGS.md); the headline result has a standalone study at [reports/ink_detection_64px_window_study_2026-06.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/ink_detection_64px_window_study_2026-06.md).

- **Direct ink detection at the 0.5 mm / 64 px prize window is learnability-limited — a reproducible negative result.** Across six experiments and two controls, a fresh model *memorizes* 16 ink patches to pixel AUC 1.0 in 100 steps, yet cannot learn ink from a full fragment at 64 px (flat ~0.51 pooled pixel AUC, with or without augmentation, across a 12 h schedule). The decisive control: the **identical** training regime fits a synthetic CT-derived target to **0.99** in ~300 steps while real ink stalls at ~0.51 — ruling out capacity, pipeline, data quantity, compute, augmentation, and the optimization regime. The binding constraint is the window itself: at 64 px, ink is not a learnable function of the CT patch for direct supervised detection with this preprocessing (scope stated honestly in the study — not a claim that no representation could). The 0.5 mm hallucination rule that forbids large-context models also forbids the context this signal appears to need.
- **Validation metrics are artifact-saturated.** On ink-rich patches (~60% ink), a near-constant predictor scores Dice ≈ 0.75; so Dice/`val_bpb` alone don't prove a model localizes ink. Pooled pixel AUC is the honest signal (0.5 = chance), and it is what exposes the result above.
- **Large-context approaches don't fit the window.** The 2023 GP-winning TimeSformer, retrained at 64 px, reaches only per-patch AUC ~0.49 train / ~0.56 val — its strength needs the 256 px context the rule forbids; a LeJEPA self-supervised checkpoint is likewise window-incompatible (only ~20% of its encoder loads at 64 px). A clDice late-fine-tune degrades centerline overlap.
- **The 2023 Grand-Prize pipeline reproduces here, and the gap was ours, isolated one variable at a time.** Retrained in this environment, the winning TimeSformer recipe reads legible Greek letters and reaches held-out per-patch AUC **0.905**; fed *our* Scroll-1 data through that proven pipeline it still reaches **0.711**, where our own loop sits at ~0.56 on the identical data. So the deficit was never the data, labels, or environment — it was our model/training stack, and the rigor localized it instead of guessing. (Full arc: FINDINGS.md "GP-winner replication" Phases 1–4.)
- **A topology "readiness" gate we inherited is provably invalid for ink detection — a second, sharper instance of metrics misleading.** The loop gated submittability on a skeleton-distance metric (`skel_dist ≤ 2.0`) borrowed from villa's *3D fiber/surface* evaluation track. A four-case probe ([scripts/probe_skel_dist_validity.py](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/scripts/probe_skel_dist_validity.py)) shows it is a symmetric-KL divergence between *skeleton branch-length histograms* — blind to spatial location and recall (a prediction shifted **completely off** the label scores 0.0 and passes; 60 % recall passes) and hypersensitive to the fragmentation that thresholding any real probability map produces (a spatially-correct but broken centerline fails by ~20×). It is uncorrelated with detection quality, so *no* model — including the AUC-0.9 TimeSformer above — can pass it. We removed it as a gate; the honest readiness signal is pixel-AUC plus human legibility. (FINDINGS.md "Phase 4b".)
- **Bugs found and fixed via the rigor.** A Frangi fiber target silently trained on zeros; five of nine sampled augmentations were silent no-ops; the ridge feature channel was silently all-zeros (a cuSolver/backend bug in upstream tooling); a pseudo-label inference path mis-aligned patches by ±32 px until caught in review — all fixed.

## Honest current results

Measured by the artifact-free metric (pooled pixel AUC, 0.5 = chance), a
prize-compliant 64 px detector trained from scratch sits at the chance floor on
held-out data (~0.49–0.52), and the controls above show this is the window, not a
fixable training problem. The long-running search loop's production checkpoint
reaches ~0.557 pixel AUC, but that reflects warm-start accumulation across many
cycles rather than a fresh-trainable signal — it is marginally above chance, not a
working detector. We state this plainly: **the contribution is the open tooling and
the rigorous, reproducible negative result, not a state-of-the-art model.** That a
careful evaluation overturns optimistic Dice-based readings (Dice ≈ 0.75 from a
near-constant predictor) is itself part of the methodological contribution.

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
