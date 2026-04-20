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

## [2026-04-20] Day Shift: Scalability & Convergence Optimization (v2.2.0)

**Status:** INITIALIZING (Scheduled: 11:15 - 19:00)

### Purpose
Deploy the **v2.2.0 Frontier Architecture** (Windowed Spatial Attention) to further optimize convergence and explore higher-resolution patch sizes without OOM risks.

### Configuration
*   **Architecture:** v2.2.0 (Windowed Attention + Budget-Aware Scheduling).
*   **Target:** `val_bpb` improvement over `0.2662`.
*   **Technique:** Linear LR Scaling (`lr * batch_size/16`) to stabilize optimization across varying batch sizes.

### Outcomes & Insights
*(To be populated as cycles complete)*

---

## [Future Entry Template]

## [YYYY-MM-DD] Night Shift: [Experiment Title]

### Purpose
[Briefly describe the goal of this sprint]

### Configuration
*   **Training Source:** [e.g., Scroll 1 Monster]
*   **Validation Target:** [e.g., Scroll 5]
*   **Key Tweaks:** [e.g., Extreme Augmentation, Denoising Backbone]

### Outcomes & Insights
*   **Best val_bpb:** [X.XXXX]
*   **Winning Mutation:** [e.g., blocks_16]
*   **Key Insight:** [What did the agents discover that we didn't expect?]
