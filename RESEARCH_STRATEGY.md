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

### Diversity & Pretraining (The "Foundation" Set)
*   **36 Public Scrolls:** 1GB samples each (~36GB total) for self-supervised pretraining (DINO).
*   **Targeted Divisions (Scrolls 1, 2, 3, 5):** 11x 1GB depth slices per scroll to target specific prize regions (e.g., colophons in `div_100`).

---

## 3. Reproducibility & Methodology

To comply with submission criteria, our solution is designed for 100% automated reproduction:
*   **Docker Image:** A `Dockerfile` is provided to reconstruct the entire environment.
*   **System Requirements:** RTX 4090 (or equivalent 24GB VRAM GPU), 64GB RAM, 250GB Disk.
*   **Programmatic Output:** All submission images are generated directly from CT data by `predict.py`, which automatically appends a **1 cm scale bar** and records the **3D coordinate metadata**.

---

## 4. Prize-Specific Target Workflows

To win the **First Letters ($60k)** and **First Title ($60k)** prizes, we are deploying specialized sub-sprints:

### A. The "Scroll 2/3 First Letters" Sprint
*   **Target:** Scrolls 2 (PHerc0125) and 3 (PHerc0332).
*   **Objective:** Discover 10+ legible letters in a 4cm² area.
*   **Method:** 
    *   Exhaustive inference on our **11x 1GB depth divisions** for these scrolls.
    *   Autoresearch optimization for **extreme denoising** (Scroll 2 is significantly noisier than Scroll 1).
    *   **Ensemble Voting:** Use the top 3 architectures from the Night Shift to "vote" on ink pixels to reduce false positives.

### B. The "First Title" inner-most Wrap Search
*   **Target:** Inner-most 5% of Scrolls 1, 2, and 3.
*   **Objective:** Locate the title (colophon) usually found at the end of the scroll.
*   **Method:**
    *   **Division 100% Focus:** Prioritize our `div_100` local datasets, which represent the core of the scrolls.
    *   **Spatial Context Rendering:** Update `predict.py` to output 3D contextual visualizations (showing where the ink sits relative to the papyrus surface) to satisfy the "Team of Papyrologists" legibility requirement.

---

## 5. Prize Readiness Audit (Compliance Checklist)

Our workflow is strictly engineered to win the following high-value prizes:

### **A. First Letters Prize ($60,000)**
*   **Target:** Scrolls 2 and 3.
*   **Audit:**
    *   [x] **Data Coverage:** 11x 1GB divisions per scroll (0% to 100% depth) are stored locally for exhaustive search.
    *   [x] **Hardware:** RTX 4090 enables rapid inference over these 22GB of data.
    *   [x] **Validation:** Models are evolved to handle the specific noise profile of Scroll 2.

### **B. First Title Prize ($60,000)**
*   **Target:** Scrolls 1, 2, and 3.
*   **Audit:**
    *   [x] **Region Focus:** Systematic prioritization of `div_100` (inner-most wraps) where colophons are traditionally located.
    *   [x] **Visualization:** `predict.py` automatically generates 3-panel context images (CT + Fiber + Ink) with programmatic 1cm/1mm scale bars.
    *   [x] **Verification:** Metadata JSON includes precise 3D coordinates and segmentation IDs for scholar verification.

## 6. Daily Operational Workflow

| Time | Action | Responsibility |
| :--- | :--- | :--- |
| **08:00 AM** | **Morning Review** | Human + LLM: Analyze `NightShift_Analysis.ipynb` and `reports/figures/`. |
| **08:15 AM** | **Generate Reports** | Run `python3 plot_results.py` and `python3 scripts/generate_daily_report.py`. |
| **08:45 AM** | **Paper Update** | Update `RESEARCH_PAPER.md` with new findings and winning mutations. |
| **09:00 AM** | **Winning Merge** | Merge the best-performing architecture into `main`. |
| **10:00 AM** | **Full-Scale Inference** | Use the winning model to generate ink-maps for new, unseen segments. |
| **12:00 PM - 06:00 PM** | **Cooldown / Feature Dev** | Clean up code, implement new features, or handle manual downloads. |
| **07:00 PM** | **Launch Night Shift** | Kick off the autonomous loop for another 12 hours. |
