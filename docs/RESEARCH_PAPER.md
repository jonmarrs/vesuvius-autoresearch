# Autonomous Architectural Evolution for 3D Ink Detection in Carbonized Herculaneum Scrolls

**Author:** Jon Marrs

**Status:** Draft / in-progress research notes — not a submitted paper. Numbers and claims here track the current state of the [`vesuvius-autoresearch`](https://github.com/jonmarrs/vesuvius-autoresearch) loop and are updated as cycles complete; treat as a living document until a version is explicitly submitted somewhere.

## Abstract
Detecting ink within micro-CT scans of carbonized papyrus scrolls remains a significant challenge due to low signal-to-noise ratios, morphological variability across scrolls, and the risk of model hallucination. These notes describe an autonomous research loop that uses a Thompson-sampling bandit over architectural and hyperparameter tweaks to evolve 3D ink-detection models on a single workstation GPU (NVIDIA RTX 4090). The loop runs in two cadence modes — a 15-minute Day Shift and a 60-minute Night Shift — and gates promotions on a fixed `val_bpb` baseline measured against an ink-aware validation sampler (commit `c9f578f`). On held-out PHerc Paris 2 Fragment 143 the production `resenc_unet` reports `val_bpb` ≈ 0.2627 and `centerline_dice` ≈ 0.30 (at the topology-optimal threshold). The headline methodological finding is that these validation metrics are *artifact-saturated* — a near-constant predictor scores Dice ≈ 0.75 on ink-rich patches — so per-patch discrimination AUC (≈ 0.74 train / 0.61 val) is the honest signal. Cross-scroll generalization to Scroll 2 / Scroll 3 is unproven and is the active research target, not a claimed result.

## I. Introduction
The Vesuvius Challenge seeks to read the lost library of Herculaneum through advanced imaging and machine learning. While significant progress has been made on unrolled fragments, the "Generalization Gap" — the failure of a model trained on one scroll to detect ink on another — remains the primary bottleneck for the $1M Grand Prize.

Manual architectural tuning is slow. The autoresearch loop attempts to compress that loop by running 15-minute (Day Shift) or 60-minute (Night Shift) experimental cycles autonomously, mutating a small number of axes (learning rate, capacity, augmentation knobs, loss balance, auxiliary tasks, etc.) per cycle and promoting only configurations that improve `val_bpb` over the held checkpoint.

## II. Methodology

### A. Model Architecture
The bandit's `architecture` family samples from `{lejepa_unet, resenc_unet, timesformer, resnet3d_decoder}`. The current production checkpoint is `resenc_unet` (pinned for fine-tuning); a LeJEPA self-supervised pretrain (`checkpoints/lejepa_foundation_v1/`) is available as an initializer. The `timesformer` option provides Multi-head Temporal Attention across the Z-axis; the others are convolutional UNet variants. None of these claims to be a novel architecture — the contribution is the autonomous search over an existing zoo, not a new model.

### B. Autonomous Evolution Framework
The loop's tweak axes (currently 19 families): learning rate, weight decay, capacity (`num_blocks`), attention head count, dropout, lasagna preprocessing toggle, batch size, patch size, temporal depth (`num_layers`), width (`base_feat`), per-task loss weights (ink/dice/fiber/structure-tensor), ridge/Frangi feature toggle and sigma, augmentation mode (Albumentations vs batchgeneratorsv2), architecture, nine scroll-specific augmentation probabilities (decohesion, warping, squeeze, z-dropout, intensity-drift, sheet-compression, thick-slice, rician-noise, blank-rectangles); a 2026-06 fix unified these into one library after finding five were silent no-ops, foundation-model path, pseudo-label directory, UA-MT toggle and EMA / consistency hyperparameters, and as of 2026-05-16 the auxiliary multi-task heads toggle. A Thompson-sampling-style bandit weights families by recent success (`autoresearch_history.json`).

### C. Data Strategy
Training pool is currently `local_data/PHercParis2Fr47/surface_volume.zarr` (PHerc Paris 2 Fragment 47), with an additional unlabeled set for Mean-Teacher / consistency regularization (`PHercParis2Fr143`, `PHercParis2Fr47`). Validation runs on `local_data/PHercParis2Fr143/surface_volume.zarr` — a held-out fragment from the same scroll. This is *fragment-level* validation; it is not cross-scroll, and we do not currently claim a measured Scroll 2 / Scroll 3 transfer number. Cross-scroll generalization is the active research target rather than a result. The CT-derived pseudo-label generators in [ScrollPrize/villa#922](https://github.com/ScrollPrize/villa/pull/922) (fiber) and [#923](https://github.com/ScrollPrize/villa/pull/923) (3D ink) are part of the infrastructure intended to support that target.

### D. Resource Constraints and Citizen Science Accessibility
In the spirit of citizen science and decentralized science (DeSci), our framework is designed to be accessible to researchers with standard high-end consumer hardware and typical internet connectivity. We strictly limit resource consumption to ensure that the methodology remains tolerable for individual contributors:
*   **Data Bandwidth:** We maintain a monthly download limit of **500 GB**, achieved through a targeted "download once, train indefinitely" offline-first strategy.
*   **Local Storage:** We cap local data storage at **500 GB** at any given time, prioritizing high-value labeled segments over full scroll volumes.

## III. Experimental Setup
Experiments run on an NVIDIA RTX 4090 (24 GB VRAM). We enforce a 0.5 × 0.5 mm (64 × 64 voxel at 7.91 µm spacing) prediction window per the Vesuvius Challenge hallucination guidance for ink detection. The loop runs continuously during Day Shift (07:00–19:00 local, 900 s/cycle) and Night Shift (otherwise, 3600 s/cycle).

## IV. Current Results

### A. Model performance
The production `resenc_unet` reports `val_bpb` ≈ 0.2627 and `centerline_dice` ≈
0.30 (topology-optimal threshold) on held-out Fragment 143. Per-patch ink-vs-
background AUC is ≈ 0.74 (train) / 0.61 (val). The validation metrics are
artifact-saturated (a near-constant predictor scores Dice ≈ 0.75 on ink-rich
patches), so AUC is the honest discrimination signal. See `FINDINGS.md` for the
full honest results and the artifact-saturation analysis. (An earlier evaluation
contained a documented zero-Dice validation wall, fixed in `c9f578f`.)

### B. GPU fiber/ridge detection
A closed-form symmetric-3×3 eigensolver replaces the cuSolver `eigvalsh` path
that fails on large Hessian batches, enabling 14–94× dense speedups over NumPy
(64³–256³) and tiled 512³ execution in ~3–5 s at ~1 GB VRAM (float64 eigenvalue
parity 3.1e-10). This was proposed upstream as ScrollPrize/villa#1033 (closed
without review); the maintained version lives in this repo. Earlier `vesuvius-c`
binding PRs (#914/#916) and CuPy-acceleration PRs (#915) were also closed and are
superseded by the closed-form path above.

### C. What's open
- Closing the topology gap: `skeleton_distance_length` ≈ 19.8 vs the prize gate of 2.0. This is a model-quality problem (the detector's per-patch AUC is only ≈ 0.61 on validation), not a search-tuning one.
- Lifting discrimination via SSL pretraining (LeJEPA) and the richer (now-active) scroll augmentations, and closing the train→val generalization gap (AUC 0.74→0.61).
- Whether CT-derived fiber / 3D-ink pseudo-labels produce useful expanded supervision when mixed into training (the generators live in this repo).
- Setting up a true cross-scroll evaluation target (Scroll 2 / Scroll 3 surfaces, no manual labels) via the CT-derived pseudo-labels as a downstream evaluator.

## V. Discussion
The earlier "`val_bpb` plateau" was partly an evaluation artifact: validation metrics are artifact-saturated (a near-constant predictor scores Dice ≈ 0.75), and topology metrics were being read at the Dice-optimal threshold, which understates them ~2×. Fixing the evaluation (topology-optimal thresholding, topology-first selection with a noise tolerance) and fixing two latent bugs (a zeros-only Frangi fiber target; five of nine scroll augmentations that were silent no-ops) unblocked real movement — `centerline_dice` climbed 0.198 → ~0.30. The remaining gap is genuine model quality: per-patch ink AUC ≈ 0.61 on held-out data, so the next-level levers are better/longer training, SSL pretraining, and supervised-data expansion, not more hyperparameter search. A negative result reinforces this: the 2023 GP-winning TimeSformer, trained at the 64 px prize window, underperforms the CNN (its strength needs a 256 px context the hallucination rule forbids).

## VI. Conclusion
Notes-to-self status. The infrastructure (bandit loop, evidence chain, pseudo-label generators, villa PR stack) is in place. The remaining work is research, not engineering.

## References
[1] Seales, B., et al. "Reading the Scrolls of Herculaneum," EduceLab, 2023.
[2] Karpathy, A. "Autoresearch Methodology," 2025.
[3] Vesuvius Challenge Technical Requirements, 2026.
