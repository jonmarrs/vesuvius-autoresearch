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
