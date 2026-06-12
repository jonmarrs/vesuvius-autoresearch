# June 2026 Progress Prize — Filing Draft

**Status:** DRAFT for review. Deadline 2026-06-30 11:59pm PT. File via the official Progress Prize form once it opens.
**Repository (the submission artifact):** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)
**Live experiment tracking:** https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

> Internal notes for filing (delete before submission): no AI-authorship markers anywhere. Lead with the open-source tools and the honest methodology, not the model's accuracy. Cite the public fork branch for the fibers work; do not present the closed May PRs as merged. Numbers below are from `best_model.pt` / committed evidence as of 2026-06-11 — refresh if cycles have moved them before filing.

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

## Findings (the methodological contribution)

Documented in full at [FINDINGS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/FINDINGS.md):

- **Validation metrics are artifact-saturated.** On ink-rich patches (~60% ink), a near-constant predictor scores Dice ≈ 0.75; so Dice/`val_bpb` alone don't prove a model localizes ink. Per-patch AUC is the honest signal (the production model: ≈ 0.74 train / 0.61 val).
- **Topology metrics depend on the binarization threshold.** At the Dice-optimal threshold they understate topology ~2×; the same model reports `centerline_dice` 0.073 → 0.198 just by thresholding at the topology-optimal point.
- **Honest negative results.** A clDice late-fine-tune degrades centerline overlap; the 2023 GP-winning TimeSformer, retrained at the 0.5 mm (~64 px) prize window, underperforms a CNN — its strength needs a 256 px context the hallucination rule forbids.
- **Bugs found and fixed via the rigor.** A Frangi fiber target silently trained on zeros; five of nine sampled augmentations were silent no-ops; the ridge feature channel was silently all-zeros (a cuSolver/backend bug in upstream tooling) — all fixed and decoupled from the broken dependency.

## Honest current results

Production `resenc_unet` on held-out `PHercParis2Fr143` (disjoint from the training fragment): `val_bpb` 0.2627, `centerline_dice` ~0.30 (topology-optimal threshold), per-patch ink AUC ~0.74 train / 0.61 val. Mediocre but improving (over the recent cycle window: train AUC 0.70→0.74, `centerline_dice` 0.198→0.30). Cross-scroll transfer to Scrolls 2–3 is unproven and is the stated research target, not a claim.

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
- Augmentations: .../blob/main/docs/SCROLL_AUGMENTATIONS.md
- Fiber detection: .../blob/main/docs/FIBER_DETECTION.md
- wandb: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch
