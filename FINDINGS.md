# Findings

An autonomous, evidence-gated ink-detection research loop for the Vesuvius
Challenge, running continuously on a single NVIDIA RTX 4090. This document is the
honest record: what the tools do, how the model actually performs, and what the
search has taught us — including the negative results.

## Deliverables (tools)

- **Autoresearch loop** (`run_autoresearch_loop.py`) — a bandit samples
  architecture / loss / augmentation / hyperparameter "families", trains each
  candidate under a fixed wall-clock budget on a single GPU, evaluates on a
  held-out fragment, and promotes only topology-improving configurations.
- **Scroll-specific augmentation library** (`scroll_augmentations.py`) — nine
  GPU-native augmentations modeling scroll-CT artifacts; addresses
  [villa #201](https://github.com/ScrollPrize/villa/issues/201). See
  [docs/SCROLL_AUGMENTATIONS.md](docs/SCROLL_AUGMENTATIONS.md) and the
  [before/after demo](reports/augmentation_demos/all_families.png).
- **GPU fiber/ridge detection** — a closed-form symmetric-3×3 eigensolver that
  avoids the cuSolver `eigvalsh` failure on large Hessian batches, with tiled
  execution: dense 14–94× over NumPy (64³–256³), 512³ tiled in ~3–5 s at ~1 GB
  VRAM, float64 eigenvalue parity 3.1e-10. See
  [reports/fibers_gpu_validation_2026-06.md](reports/fibers_gpu_validation_2026-06.md).
- **Experiment tracking** — opt-in Weights & Biases logging (parameter/gradient
  histograms, per-cycle metrics, prediction images), mirroring villa's setup.
  Live: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch
- **Topology-aware evaluation toolkit** — selects the binarization threshold that
  maximizes centerline overlap and reports the prize topology metrics there
  (see "What we learned").

## Honest current results

Production model: `resenc_unet`, evaluated on held-out `PHercParis2Fr143`
(disjoint from the `PHercParis2Fr47` training fragment).

| Metric | Value | Note |
| --- | --- | --- |
| `val_bpb` | 0.2627 | 1 − Dice at the Dice-optimal threshold |
| `centerline_dice` | ~0.30 | at the topology-optimal threshold; up from 0.198 |
| `skel_dist` | ~19.8 | prize gate is 2.0 — large remaining headroom |
| ink AUC (train Fr47) | 0.74 | per-patch ink-vs-background discrimination |
| ink AUC (val Fr143) | 0.61 | 0.5 = chance |

This is a mediocre-but-improving detector, stated plainly (over the recent cycle
window: train AUC 0.70→0.74, val 0.60→0.61, `centerline_dice` 0.198→0.30). The
contribution is the reproducible, evidence-gated search process and the tooling
around it — not a state-of-the-art model.

## What we learned

- **Validation metrics are artifact-saturated.** On ink-containing patches
  (~60% ink), a near-constant predictor scores Dice ≈ 0.75 at a low threshold.
  So `val_bpb` / Dice alone do not prove a model localizes ink; per-patch AUC
  exposed that the production model sits at ~0.74 train / ~0.61 val.
- **Topology metrics depend on the threshold.** Evaluating `centerline_dice` /
  `skel_dist` at the Dice-optimal threshold understates topology by ~2×; at the
  topology-optimal threshold the *same* model reports `centerline_dice`
  0.073 → 0.198. The loop now selects and reports at the topology-optimal point.
- **Negative results (kept honest):**
  - *clDice as a late fine-tune* of the converged model degrades centerline
    overlap (cl_dice 0.073–0.077), rather than improving it — the soft skeleton
    is a poor proxy on a diffuse, under-confident model.
  - *The GP-winning TimeSformer at the 64 px prize window* reaches only AUC
    ~0.49 train / ~0.56 val. Its strength needs the 256 px context that the
    Challenge's 0.5 mm (~64 px) hallucination window forbids; at 64 px a CNN
    that emits full-resolution per-pixel output is the better fit.
  - *The LeJEPA self-supervised pretrain is unusable as a 64 px init.* The
    checkpoint was pretrained at a large input window (positional embeddings for
    1024 patches at patch-size 8³, i.e. ~64×64×128) so only ~20% of its encoder
    tensors are shape-compatible with a prize-compliant `lejepa_unet` at
    16×64×64 (128 patches); matching it would require the same oversized context
    the 64 px hallucination window forbids (and the checkpoint is an early
    epoch-9 pretrain). Same structural constraint as the TimeSformer result:
    large-context approaches don't fit the prize window.
  - *The cross-scroll generalization gap is severe — and brief multi-scroll
    fine-tuning does not close it.* Measured on a genuinely held-out scroll
    (PHerc1667Fr3, never in training), the production model scores pooled
    pixel-AUC **0.492 — exactly chance** (vs 0.565 on its own scroll): it has
    essentially zero cross-scroll transfer. Warm-starting and fine-tuning the
    64 px resenc CNN on three scrolls (Fr47 + PHercParis1 Fr34/Fr39 + PHerc51
    Fr8) for an hour left the held-out AUC unchanged (0.492 → 0.492). Caveat:
    throughput was only ~550 steps/hr — loading patches from four large
    multi-scroll volumes is the bottleneck — so this tests a *brief* fine-tune,
    not thorough multi-scroll training. Closing the gap (the Grand Prize
    bottleneck) will need a faster patch pipeline + far more training, or a
    fundamentally different transfer approach.
- **Bugs surfaced by the rigor:** the Frangi fiber target silently trained on
  zeros (a backend bug in the upstream `tools.py`), and 5 of 9 sampled
  augmentation families were silent no-ops until the augmentation code was
  unified into one library. Both are fixed.

## Reproduce

See the [README](README.md) quick start to install and run a cycle, and the live
[wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch) for
streaming metrics.
