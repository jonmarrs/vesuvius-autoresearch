# Autonomous Architectural Evolution for 3D Ink Detection in Carbonized Herculaneum Scrolls

**Author:** Jon Marrs

**Status:** Draft / in-progress research notes — not a submitted paper. Numbers and claims here track the current state of the [`vesuvius-autoresearch`](https://github.com/jonmarrs/vesuvius-autoresearch) loop and are updated as cycles complete; treat as a living document until a version is explicitly submitted somewhere.

## Abstract
Detecting ink within micro-CT scans of carbonized papyrus scrolls remains a significant challenge due to low signal-to-noise ratios, morphological variability across scrolls, and the risk of model hallucination. These notes describe an autonomous research loop that uses a Thompson-sampling bandit over architectural and hyperparameter tweaks to evolve 3D ink-detection models on a single workstation GPU (NVIDIA RTX 4090). The loop runs in two cadence modes — a 15-minute Day Shift and a 60-minute Night Shift — and gates promotions on a fixed `val_bpb` baseline measured against an ink-aware validation sampler (commit `c9f578f`). The current best `val_bpb` on the in-distribution PHerc Paris 2 Fragment 143 surface volume is **0.4145**; cross-scroll generalization to Scroll 2 / Scroll 3 is unproven and is the active research target rather than a claimed result.

## I. Introduction
The Vesuvius Challenge seeks to read the lost library of Herculaneum through advanced imaging and machine learning. While significant progress has been made on unrolled fragments, the "Generalization Gap" — the failure of a model trained on one scroll to detect ink on another — remains the primary bottleneck for the $1M Grand Prize.

Manual architectural tuning is slow. The autoresearch loop attempts to compress that loop by running 15-minute (Day Shift) or 60-minute (Night Shift) experimental cycles autonomously, mutating a small number of axes (learning rate, capacity, augmentation knobs, loss balance, auxiliary tasks, etc.) per cycle and promoting only configurations that improve `val_bpb` over the held checkpoint.

## II. Methodology

### A. Model Architecture
The bandit's `architecture` family samples from `{lejepa_unet, resenc_unet, timesformer, resnet3d_decoder}`. The current best checkpoint is `lejepa_unet` initialized from a LeJEPA self-supervised pretraining stage (`checkpoints/lejepa_foundation_v1/`). The `timesformer` option provides Multi-head Temporal Attention across the Z-axis; the others are convolutional UNet variants. None of these claims to be a novel architecture — the contribution is the autonomous search over an existing zoo, not a new model.

### B. Autonomous Evolution Framework
The loop's tweak axes (currently 19 families): learning rate, weight decay, capacity (`num_blocks`), attention head count, dropout, lasagna preprocessing toggle, batch size, patch size, temporal depth (`num_layers`), width (`base_feat`), per-task loss weights (ink/dice/fiber/structure-tensor), ridge/Frangi feature toggle and sigma, augmentation mode (Albumentations vs batchgeneratorsv2), architecture, four scroll-specific augmentation probabilities (decohesion/squeeze/z-dropout/intensity-drift), foundation-model path, pseudo-label directory, UA-MT toggle and EMA / consistency hyperparameters, and as of 2026-05-16 the auxiliary multi-task heads toggle. A Thompson-sampling-style bandit weights families by recent success (`autoresearch_history.json`).

### C. Data Strategy
Training pool is currently `local_data/PHercParis2Fr47/surface_volume.zarr` (PHerc Paris 2 Fragment 47), with an additional unlabeled set for Mean-Teacher / consistency regularization (`PHercParis2Fr143`, `PHercParis2Fr47`). Validation runs on `local_data/PHercParis2Fr143/surface_volume.zarr` — a held-out fragment from the same scroll. This is *fragment-level* validation; it is not cross-scroll, and we do not currently claim a measured Scroll 2 / Scroll 3 transfer number. Cross-scroll generalization is the active research target rather than a result. The CT-derived pseudo-label generators in [ScrollPrize/villa#922](https://github.com/ScrollPrize/villa/pull/922) (fiber) and [#923](https://github.com/ScrollPrize/villa/pull/923) (3D ink) are part of the infrastructure intended to support that target.

### D. Resource Constraints and Citizen Science Accessibility
In the spirit of citizen science and decentralized science (DeSci), our framework is designed to be accessible to researchers with standard high-end consumer hardware and typical internet connectivity. We strictly limit resource consumption to ensure that the methodology remains tolerable for individual contributors:
*   **Data Bandwidth:** We maintain a monthly download limit of **500 GB**, achieved through a targeted "download once, train indefinitely" offline-first strategy.
*   **Local Storage:** We cap local data storage at **500 GB** at any given time, prioritizing high-value labeled segments over full scroll volumes.

## III. Experimental Setup
Experiments run on an NVIDIA RTX 4090 (24 GB VRAM). We enforce a 0.5 × 0.5 mm (64 × 64 voxel at 7.91 µm spacing) prediction window per the Vesuvius Challenge hallucination guidance for ink detection. The loop runs continuously during Day Shift (07:00–19:00 local, 900 s/cycle) and Night Shift (otherwise, 3600 s/cycle).

## IV. Current Results

### A. `val_bpb` baseline
Under the post-`c9f578f` ink-aware validation (the prior evaluation contained a documented zero-Dice validation wall — see annotation in [`PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md`](PROGRESS_PRIZE_SUBMISSION_2026-05.md)), the loop converges to `val_bpb ≈ 0.4145` on the PHerc Paris 2 Fragment 143 validation volume. This is the model's honest in-distribution performance; it is **not** a cross-scroll claim. The bandit has been at this plateau since 2026-05-05.

### B. Throughput / data path
The vesuvius-c Python bindings ([`vesuvius_c_wrapper/`](https://github.com/jonmarrs/vesuvius-autoresearch/tree/main/vesuvius_c_wrapper) in this repo; upstreamed in [ScrollPrize/villa#916](https://github.com/ScrollPrize/villa/pull/916)) measure ~31.77 M voxels/sec for zero-copy Blosc2 chunk reads on local storage. CuPy acceleration of the fiber-detection preprocessing ([ScrollPrize/villa#915](https://github.com/ScrollPrize/villa/pull/915)) measures `nms_3d` 430× at 256³, `hessian` 226×, `detect_ridges` 82× vs the NumPy baseline.

### C. What's open
- Whether enabling the auxiliary multi-task heads (surface_normals + structure_tensor, added to the bandit's search space on 2026-05-16) breaks the `val_bpb` plateau.
- Whether the CT-derived fiber and 3D ink pseudo-labels from villa PRs #922 / #923 produce useful expanded supervision when mixed into training.
- Whether a true cross-scroll evaluation target (Scroll 2 / Scroll 3 surfaces, where there are no manual labels) can be set up via the CT-derived pseudo-labels as a downstream evaluator.

## V. Discussion
The current plateau looks structural rather than search-failure-shaped: 14 Day Shift cycles on 2026-05-16 explored loss balance, capacity, learning rate, regularization, augmentation, and lasagna preprocessing, all reverted at the same `val_bpb`. The bandit's `auxiliary_config.enabled` axis was the missing search dimension, which is now in rotation. If that also fails to move the metric, the next-level levers are validation-target redesign and supervised-data expansion, not more hyperparameter search.

## VI. Conclusion
Notes-to-self status. The infrastructure (bandit loop, evidence chain, pseudo-label generators, villa PR stack) is in place. The remaining work is research, not engineering.

## References
[1] Seales, B., et al. "Reading the Scrolls of Herculaneum," EduceLab, 2023.
[2] Karpathy, A. "Autoresearch Methodology," 2025.
[3] Vesuvius Challenge Technical Requirements, 2026.
