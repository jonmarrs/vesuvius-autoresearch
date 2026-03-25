# Vesuvius Autoresearch Strategy: Systematic Progress Plan

This document outlines the systematic research strategy for winning Vesuvius Challenge prizes, specifically focusing on ink detection while operating within strict hardware, storage, and bandwidth constraints.

## 1. Constraints & Optimization

To maintain a sustainable and high-impact research trajectory, all workflows must respect the following limits:

*   **GPU (RTX 4090):** 
    *   **VRAM:** 24 GB. 
    *   **Target:** Move beyond 64x64 patches. Optimize for **128x128 or 256x256 patches** to provide the model with more spatial context for ink morphological features.
    *   **Throughput:** Aim for >50M voxels/sec by utilizing the 4090's high compute density.
*   **Storage:** 
    *   **Project Limit:** 250 GB total. 
    *   **Current Usage:** ~110 GB.
    *   **Policy:** Prioritize **labeled segment-volume pairs** over full scroll volumes. Delete "empty" scroll divisions as needed to make room for high-value ground truth.
*   **Bandwidth:** 
    *   **Project Limit:** 500 GB / month.
    *   **Current Usage:** ~150 GB (March 2026).
    *   **Policy:** **Offline-First Workflow.** Download data once, store it locally in `local_data/`, and train indefinitely without further streaming.

---

## 2. Data Strategy: The "Gold Standard" Library

To win prizes, we must optimize against **real ground truth** rather than synthetic targets. Our local library focuses on highly-aligned labeled data.

### High-Priority Labeled Fragments (The "Supervised" Set)
| Dataset | Source | Type | Status |
| :--- | :--- | :--- | :--- |
| **Frag 1 (Paris 2 Fr 47)** | dl.ash2txt.org | Full Volume (32 layers) | Downloading |
| **Frag 2 (Paris 2 Fr 143)** | dl.ash2txt.org | 1GB Sample (32 layers) | Complete |
| **Frag 5 (PHerc1667Cr1Fr3)** | dl.ash2txt.org | 1GB Sample (32 layers) | Complete |
| **Frag 6 (PHerc51Cr4Fr8)** | dl.ash2txt.org | 1GB Sample (32 layers) | Complete |
| **Scroll 1 Monster (20231012184424)** | dl.ash2txt.org | 1GB Sample (32 layers) | Queued |
| **Scroll 4 Segment (20231210132040)** | dl.ash2txt.org | 1GB Sample (32 layers) | Queued |

### Diversity & Pretraining (The "Foundation" Set)
*   **36 Public Scrolls:** 1GB samples each (~36GB total) for self-supervised pretraining (DINO) and synthetic ink injection to learn general papyrus texture.

---

## 3. The "Night Shift": Autonomous Research Loop

Following the Karpathy-style autoresearch method, we deploy a swarm of automated iterations to evolve our models.

*   **Schedule:** 7:00 PM - 7:00 AM (Daily).
*   **Method:** 
    *   **Iteration Time:** 5-minute training cycles.
    *   **Throughput:** ~144 experiments per night.
    *   **Mechanism:** LLM acts as the primary researcher—modifying `train.py`, committing changes, analyzing results, and advancing the branch on improvement.
*   **Core Metric:** **Cross-Scroll Dice Score.** 
    *   We train primarily on Scroll 1/Fragment 1 and validate against unseen scrolls (e.g., validating on Scroll 5 or Paris fragments). 
    *   A model that generalizes across scrolls is the key to winning the $1M Grand Prize.

---

## 4. Research Roadmap (Phases)

### Phase 1: Gold Standard Library (Current)
*   Finalize downloads of all labeled segments.
*   Update `VesuviusLabeledDataset` to handle local unrolled layer directories.
*   Baseline establish: Establish the current best Dice score on genuine labels.

### Phase 2: Architectural Backbone Evolution
*   Autoresearch competition between **3D-UNet**, **ResNet-3D**, and **Temporal Attention Hybrids**.
*   Determine the optimal patch size and depth (Z-layers) for the RTX 4090.

### Phase 3: Signal-to-Noise (SNR) Optimization
*   Evolve denoising kernels and normalization strategies (LayerNorm vs. GroupNorm vs. InstanceNorm).
*   Maximize the "Isolation Factor" to prevent ink ghosting between wraps.

### Phase 4: Data Augmentation Swarm
*   Automate the search for augmentations that improve generalization (e.g., finding the best parameters for Elastic Deformation and MixUp specifically for carbonized scrolls).

---

## 5. Daily Operational Workflow

| Time | Action | Responsibility |
| :--- | :--- | :--- |
| **08:00 AM** | **Morning Review** | Human + LLM: Analyze Night Shift winners and `results.tsv`. |
| **09:00 AM** | **Winning Merge** | Merge the best-performing architecture into `main`. |
| **10:00 AM** | **Full-Scale Inference** | Use the winning model to generate ink-maps for new, unseen segments. |
| **12:00 PM - 06:00 PM** | **Cooldown / Feature Dev** | Clean up code, implement new features, or handle manual downloads. |
| **07:00 PM** | **Launch Night Shift** | Kick off the autonomous loop for another 12 hours. |
