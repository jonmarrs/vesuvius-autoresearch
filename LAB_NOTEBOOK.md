# Vesuvius Autoresearch: Lab Notebook

This notebook serves as a high-level record of major research milestones, Night Shift experiment results, and key architectural insights discovered by the autonomous agent swarm.

---

## [2026-03-25] Night Shift: The "Gold Standard" Generalization Sprint

**Status:** IN PROGRESS (Scheduled: 18:00 - 07:00)

### Purpose
Transition from synthetic targets to genuine manual ink labels. The primary objective is to evaluate and optimize **Cross-Fragment Generalization**—the model's ability to learn ink morphology on one fragment and successfully predict it on an entirely different scan environment.

### Configuration
*   **Hardware:** RTX 4090 (24GB VRAM).
*   **Compliance:** Strictly enforced **64x64 (0.5x0.5mm)** prediction window to mitigate hallucinations.
*   **Training Source:** PHerc. Paris 2 Fr 47 (Fragment 1) - 33 unrolled layers.
*   **Validation Target:** PHerc. Paris 2 Fr 143 (Fragment 2) - 33 unrolled layers.
*   **Metric:** 1.0 - Dice Score (lower is better).
*   **Technique:** Hybrid Supervised (Manual Labels) + Self-Supervised (DINO consistency).

### Hypotheses to Test
1.  **Denoising Priority:** Does GroupNorm outperform InstanceNorm on high-noise X-ray scans like Paris fragments?
2.  **Anisotropic Bias:** Will 3D kernels biased toward the horizontal plane (fiber-aligned) capture ink better than isotropic 3x3x3 kernels?
3.  **Capacity vs. Overfit:** Finding the threshold where increasing attention heads starts hurting cross-fragment generalization.

### Outcomes & Insights
*(To be populated on 2026-03-26 08:00 AM)*

---

## [2026-04-17] Day Shift: Resuming the Gold Standard Baseline (v2.1.0)

**Status:** ACTIVE (Launched: 13:45)

### Purpose
Resume the autonomous search for model improvements after a system crash. This shift deploys the **v2.1.0 Frontier Architecture**, specifically designed to handle dynamic input geometries and mitigate model hallucinations.

### Configuration
*   **Hardware:** RTX 4090 (24GB VRAM).
*   **Target:** `val_bpb` (1.0 - Dice) improvement over the current best (0.0025).
*   **Strategy:** Automated 15-minute training cycles with Bayesian-lite parameter sampling and **Success-Biased Decay**.

### Key Architectural Updates (v2.1.0)
1.  **Dynamic Positional Interpolation:** Positional embeddings now adapt to any `patch_size` or `num_layers`.
2.  **Hallucination Penalty:** Enhanced loss function that penalizes ink detection in regions where the QC head identifies low structural complexity (non-papyrus).
3.  **Crash Resilience:** Hardened experiment tracking that persists success history across system restarts.

### Outcomes & Insights
*   **Cycle 1 (v2.1.0):** Completed with `val_bpb: 0.2981`. No improvement over baseline (0.2806), but confirmed the **Hallucination Penalty** and dynamic architecture are stable.
*   **Baseline Correction:** Fixed a `nan` value in `best_model.pt` that was caused by a previous failed run. Corrected baseline to `0.280617`.

---

## [2026-04-19] Night Shift: V2.1.0 Architecture Extended Search

**Status:** ACTIVE (Launched: 19:06)

### Purpose
Continue the autonomous search for model improvements utilizing the robust v2.1.0 architecture with dynamic positional interpolation and hallucination penalty. The primary objective remains optimizing the `val_bpb` (1.0 - Dice) for Cross-Fragment Generalization.

### Configuration
*   **Hardware:** RTX 4090 (24GB VRAM).
*   **Training Source:** PHerc. Paris 2 Fr 47 (Fragment 1) - 33 unrolled layers.
*   **Validation Target:** PHerc. Paris 2 Fr 143 (Fragment 2) - 33 unrolled layers.
*   **Key Tweaks:** Exploring full hyperparameter space with Success-Biased Decay to avoid local minima.

### Outcomes & Insights
*   **Best val_bpb:** 0.2662 (Cycle 15)
*   **Winning Mutation:** `num_layers: 24` with `dropout: 0.2`.
*   **Key Insight:** Increasing the Z-depth to 24 layers provided a significant boost in cross-fragment generalization, likely by capturing more volumetric context for ink morphology. However, attempts to scale to 32 layers triggered system crashes, suggesting a hardware limit on the current RTX 4090 memory for that specific configuration.
*   **Architectural Stability:** The v2.1.0 and subsequent v2.2.0 updates (Windowed Attention) proved highly stable, maintaining high throughput (~8-13M voxels/sec) throughout the 50-cycle run.

---

## [2026-04-20] Day Shift: Vesuvius-DINO Self-Supervised Refactor (v2.4.0)

**Status:** ACTIVE (Launched: 13:25)

### Purpose
Deploy the **v2.4.0 Vesuvius-DINO** architecture. This refactor bridges the "Grand Prize Gap" by integrating self-supervised consistency learning alongside supervised ink detection.

### Configuration
*   **Architecture:** v2.4.0 (Student-Teacher Projection + Self-Supervised Consistency Loss).
*   **New Objective:** `consistency_loss` (weight: 0.1) forcing alignment between different augmented views of the same volume patch.
*   **Inference:** Sliding window soft-tiling with Hanning blending enabled in `predict.py`.

### Outcomes & Insights
*   **Official Metric Integration:** Successfully replaced the custom `val_bpb` Dice calculation with the official Vesuvius Challenge metric from `villa/segmentation/evaluation/metrics/dice.py`.
*   **Day Shift v2.4.0/v2.5.0 Completion:** Completed the optimization loop for self-supervised consistency and initial ridge detection parameters. While no new `val_bpb` record was set, the stability of the hybrid loss function was verified.

---

## [2026-04-20] Night Shift: Frontier-R Structural Discovery (v2.5.0)

**Status:** ACTIVE (Launched: 19:06)

### Purpose
Evaluate the impact of **3D Ridge Detection (Frangi Filters)** as a primary feature channel. This shift focuses on the `use_ridges` parameter to determine if mathematical fiber directionality significantly reduces hallucination noise and improves cross-fragment generalization.

### Configuration
*   **Architecture:** v2.5.0 (Ridge-Enhanced multi-channel input).
*   **Primary Feature:** 2-channel input [CT + Ridge Map].
*   **Target:** Breakthrough `val_bpb` (below 0.262).

### Outcomes & Insights
*(To be populated as cycles complete)*

---

## [2026-04-24] Day Shift: Villa Integration & Bugfix Marathon

**Status:** STABLE (All integrations verified via smoke test)

### Strategy & Hypotheses
*   **Goal:** Resume Phase 3b "Villa Integration" and resolve the "Unknown errors" that crashed the earlier Day Shift cycles.
*   **Hypothesis 1:** The crashes were caused by a device mismatch in `batchgeneratorsv2` (Sprint 028 leakage) and a boundary error in `vesuvius_loader.py` ridge detection.
*   **Hypothesis 2:** Adding the official Villa Structure Tensor auxiliary task (Sprint 023) will improve ink sensitivity by forcing the model to understand fiber orientation.

### Key Tweaks
*   **Bugfix:** Patched `SpatialTransform` in `batchgeneratorsv2` to pass `device` to grid creation, resolving the CPU/GPU mismatch.
*   **Bugfix:** Hardened `vesuvius_loader.py` to ensure at least 3 slices for ridge detection (preventing `np.gradient` ValueError on thin volumes).
*   **Sprint 014 (Labels):** Wrapped `villa` label filling tools to work on PNGs; regenerated `inklabels_filled.png` for all 6 fragments. Updated `train.py` to prioritize these higher-quality labels.
*   **Sprint 017 (Backbones):** Added `resnet3d` and `i3d` as selectable backbones in `train.py`, importing directly from `villa/ink-detection`.
*   **Sprint 023 (Structure Tensor):** Fully integrated `StructureTensorComputer` into the training loop with a 6-channel MSE loss head.

### Outcomes & Insights
*   **Best val_bpb:** 0.0866 (Smoke test, 30s budget).
*   **Key Insight:** Auxiliary tasks like Structure Tensor computation are viable on-the-fly using GPU convolutions, providing rich structural supervision without the need for pre-computed Zarrs for every experiment. This significantly lowers the barrier to "foundation-level" training.

---

## [Future Entry Template]
