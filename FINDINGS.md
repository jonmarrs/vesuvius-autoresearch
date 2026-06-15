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
  - *Cross-scroll generalization remains unmeasured — a multi-scroll experiment
    was invalidated by a data-alignment bug, caught during debugging.* The
    cross-scroll fragments (PHercParis1 Fr34/Fr39, PHerc51 Fr8, PHerc1667 Fr3)
    store their CT volumes as `(H, depth, W)` — the depth axis is in the middle
    — whereas the loader assumes `(depth, H, W)`. So the loader read transposed,
    wrong-shaped patches and the inklabels never aligned with the CT (label
    dims ≈ the volume's `(axis0, axis2)`, not `(axis1, axis2)`). A model scores
    ~chance against misaligned labels, so the apparent "held-out AUC 0.492"
    measured nothing about generalization. A valid multi-scroll / cross-scroll
    experiment needs the loader to handle the `(H, depth, W)` axis order and the
    labels resampled to the volume grid first. (Only the two PHercParis2
    fragments, Fr47/Fr143, are correctly `(depth, H, W)` and aligned.)
  - *Same-scroll pseudo-label self-training is blocked by the detector's
    pixel-level non-discrimination — and even true same-scroll labels don't
    help.* We split the held-out fragment (Fr143) into spatially-disjoint
    "unlabeled" (U) and validation (V) regions (128 px buffer, no patch
    overlap), trained a leak-free baseline on Fr47 alone, and compared it on the
    V-region against (a) self-training on confidence-filtered pseudo-labels of
    the U-region and (b) an *oracle* trained on the U-region's true labels. The
    pseudo-labels were chance-quality — the baseline's pooled **pixel** AUC is
    ~0.49–0.50 (its probabilities collapse into ~[0.17, 0.28]; ink-vs-background
    means differ by ~0.001), so confidence filtering yields labels with AUC
    **0.502** and precision ≈ the base ink rate. More tellingly, the oracle —
    13.5 k patches of *real* same-scroll supervision — did **not** lift V-region
    pixel AUC over the Fr47-only baseline (0.49 → 0.50). The production model
    (days of training) reaches only pixel AUC ~0.557 on the same region, so this
    is the same `model-barely-discriminates-ink` ceiling, not a data-quantity
    problem: at 64 px, neither pseudo-labels nor extra true same-scroll labels
    move pixel-level discrimination. (Reusable tooling from this study:
    `scripts/spatial_split_mask.py`, `scripts/generate_pseudo_labels.py`,
    `scripts/pseudo_label_quality_report.py`, a confidence-weighted ink loss,
    and a `jitter=False` deterministic-inference path in the loader.)
  - *Training longer from scratch does not lift pixel-level detection — the
    ceiling is architectural / the 64 px window, not compute budget.* A single
    clean fresh-init resenc trained for 12 h on one continuous schedule
    (~13 k steps) produces a **flat** pooled V-region pixel-AUC learning curve:
    12 hourly probes oscillate in **0.508–0.525 (≈ chance)** from hour 1 through
    hour 11, with no upward trend. So the detector never learns pixel-level ink
    discrimination in this regime *regardless of training time* — the loop's slow
    crawl to ~0.56 is warm-start carry-over across cycles, not training-time
    headroom. Taken with the pseudo-label result (more same-scroll data, real or
    pseudo, doesn't help) and the TimeSformer/LeJEPA results (large-context
    approaches violate the 64 px window), the evidence converges: the bottleneck
    is the resenc architecture or the 0.5 mm / 64 px hallucination window itself,
    not data or compute. Next levers must be architectural — or a deliberate test
    of whether legible-ink discrimination is even feasible within the 64 px
    window. (Instrument: a gated `eval_every_steps` pixel-AUC learning-curve hook
    in train.py + `scripts/pixel_auc.py`.)
  - *...but an overfit probe then localizes that ceiling to the **training
    regime**, not capacity or the architecture.* Before building a bigger model,
    we ran a feasibility probe: a fresh resenc on a fixed batch of 16 Fr47 ink
    patches with **no augmentation** drives train pixel AUC from 0.42 to **1.0 in
    100 steps** and holds it. So the architecture can perfectly represent the
    CT→ink mapping, and the loss/optimizer pipeline is sound — **capacity and
    pipeline-bug are ruled out**. Yet under the production regime (full
    7,345-patch set + heavy augmentation) the same architecture reaches only
    ~0.58 train / ~0.52 val (Probe 0). The bottleneck is therefore
    optimization/regularization/generalization — most plausibly augmentation
    strong enough to suppress the learnable ink signal, plus a generalization gap
    — **not** model capacity. This corrects the "must be architectural" reading
    above: a bigger/different network is the wrong lever; the next experiment
    should target the training recipe (augmentation strength, regularization,
    objective). (Instrument: `scripts/overfit_probe.py`.)
- **Bugs surfaced by the rigor:** the Frangi fiber target silently trained on
  zeros (a backend bug in the upstream `tools.py`), and 5 of 9 sampled
  augmentation families were silent no-ops until the augmentation code was
  unified into one library. Both are fixed.

## Reproduce

See the [README](README.md) quick start to install and run a cycle, and the live
[wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch) for
streaming metrics.
