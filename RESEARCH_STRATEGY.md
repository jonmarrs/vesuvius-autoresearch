# Vesuvius Autoresearch Strategy: Systematic Progress Plan

This document outlines the systematic research strategy for winning Vesuvius Challenge prizes, specifically focusing on ink detection while operating within strict hardware, storage, and bandwidth constraints.

## 1. Constraints & Optimization

To maintain a sustainable and high-impact research trajectory, all workflows must respect the following limits:

*   **GPU (RTX 4090):** 
    *   **VRAM:** 24 GB. 
    *   **Constraint Compliance:** We strictly adhere to the **0.5x0.5 mm window size (64x64 pixels at 8µm)** recommended by the Vesuvius Challenge. This is our primary defense against model hallucinations.
    *   **Throughput:** Aim for >50M voxels/sec by utilizing the 4090's high compute density even with small patch sizes.
*   **Storage:** 
    *   **Project Limit:** 250 GB total. 
    *   **Current Usage:** ~110 GB.
    *   **Policy:** Prioritize **labeled segment-volume pairs** over full scroll volumes. 
*   **Data Integrity & Hallucination Mitigation:**
    *   **Zero Overlap:** We maintain a strict boundary between training and prediction regions. Prediction regions are never seen by the model during the autoresearch loop.
    *   **Cross-Scroll Validation:** The ultimate proof of signal reality is the model's ability to generalize from training on Fragment 1 to predicting on an entirely unseen scroll (e.g., Scroll 5).
    *   **Isolation Factor:** Our architecture is optimized for a high "Isolation Factor" to ensure ink signal does not bleed between papyrus wraps.

---

## 2. Data Strategy: The "Gold Standard" Library

To win prizes, we must optimize against **real ground truth** while ensuring reproducibility.

### High-Priority Labeled Fragments (Supervised & Isolated)
We utilize the provided unrolled layers to ensure our training data matches manual annotations perfectly.

| Dataset | Source | Type | Status |
| :--- | :--- | :--- | :--- |
| **Frag 1 (Paris 2 Fr 47)** | dl.ash2txt.org | Labeled Surface Volume | Downloading |
| **Frag 2 (Paris 2 Fr 143)** | dl.ash2txt.org | Labeled Surface Volume | Complete |
| **Frag 5 (PHerc1667Cr1Fr3)** | dl.ash2txt.org | Labeled Surface Volume | Complete |
| **Frag 6 (PHerc51Cr4Fr8)** | dl.ash2txt.org | Labeled Surface Volume | Complete |
| **Scroll 1 Monster** | dl.ash2txt.org | Labeled Layers | Queued |
| **Scroll 4 Segment** | dl.ash2txt.org | Labeled Layers | Queued |

---

## 3. Reproducibility & Methodology

To comply with submission criteria, our solution is designed for 100% automated reproduction:
*   **Docker Image:** A `Dockerfile` is provided to reconstruct the entire environment.
*   **System Requirements:** RTX 4090 (or equivalent 24GB VRAM GPU), 64GB RAM, 250GB Disk.
*   **Programmatic Output:** All submission images are generated directly from CT data by `predict.py`, which automatically appends a **1 cm scale bar** and records the **3D coordinate metadata**.

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
