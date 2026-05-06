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

## [2026-04-30] Night Shift: High-Budget Backbone Scaling (Resumed)

**Status:** ACTIVE (Resumed: 00:10)

### Purpose
Resume the high-budget (60-min) scaling cycles after a stall. The loop is now correctly processing architectural mutations and structural multi-task regularizers.

### Configuration
*   **Budget:** 3600s per cycle.
*   **Active Log:** `sprint_logs/sprint_log_2026-04-30_00-10-18_night_shift.md`

---

## [2026-04-29] Night Shift: High-Budget Backbone Scaling

**Status:** ACTIVE (Launched: 21:25)

### Purpose
Transition to high-budget (60-min) cycles to allow complex 3D backbones and large patch sizes (96+) to converge. Focus on evaluating the `GatedUNet` vs `ResidualEncoderUNet` stability under long-term training.

### Configuration
*   **Budget:** 3600s per cycle.
*   **Goal:** Establish definitive architectural preference for Phase 3 integration.

---

## [2026-04-29] Day Shift: Reset & Bugfix Kickoff (v2.6.0)

**Status:** COMPLETE (Shift Ended: 19:06)

### Purpose
Kick off the Day Shift Experiment Sprint after identifying and fixing critical bugs that were causing widespread cycle crashes. Reset the baseline to clear a corrupted `val_bpb: 0.0` score that was preventing monotonic optimization.

### Key Fixes (v2.6.0)
1.  **Zarr URI Correction:** Updated `ExperimentConfig` defaults in `train.py` to use the `.zarr` suffix, matching the converted OME-Zarr data.
2.  **Volume Slicing Fix:** Patched `FastVesuviusVolume` in `vesuvius_loader.py` to use multi-dimensional slicing `[z, :, :]` required by the official `Volume` class.
3.  **Baseline Injection Hardening:** Updated `run_autoresearch_loop.py` to ensure injected baseline configs inherit the correct URIs.
4.  **Baseline Reset:** Renamed corrupted `best_model.pt` and `results.tsv` (which had impossible 0.0 scores) to allow the loop to find a new, genuine best model.

### Configuration
*   **Hardware:** RTX 4090 (24GB VRAM).
*   **Goal:** Establish a new, stable baseline and resume autonomous exploration of architectures and hyperparameters.

### Outcomes & Insights
*(To be populated as cycles complete)*

---

## [2026-05-05] Night Shift: Foundation Fine-Tuning & Cross-Fragment Generalization

**Status:** ACTIVE

### Purpose
Transition from unsupervised pretraining to supervised fine-tuning. This shift focuses on leveraging the **LeJEPA Foundation Model** to improve ink detection on sparse validation fragments.

### Strategy & Hypotheses
*   **Hypothesis:** The foundation model has learned a robust representation of papyrus texture from Scroll 2, which will significantly reduce hallucinations on Fragment 143 compared to models trained from scratch.
*   **Cycles:** 1-hour cycles focusing on fine-tuning the pretrained backbone.

### Key Tweaks
*   [ ] Initialize `foundation_model_path` with `checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth`.
*   [ ] Increase training budget to 3600s.

### Outcomes & Insights
*(To be populated)*

---

## [2026-05-05] Day Shift: Villa Integration & LeJEPA Pretraining

**Status:** COMPLETE

### Purpose
Align with the official Grand Prize strategy by building a Foundation Model. This shift focuses on unsupervised pretraining on unlabeled Scroll 2 data using the official `villa` LeJEPA trainer.

### Key Achievements
1.  **LeJEPA Pretraining:** Successfully completed 10 epochs of self-supervised training on `div_90` and `div_100`.
2.  **Performance:** Achieved stable convergence (Final val loss: 0.0086).
3.  **Prize Candidates:** Prepared Vesuvius-C Python Bindings and CuPy Fiber Tools for community submission.

### Outcomes & Insights
- **Representation Found:** The model successfully learned intrinsic texture features from Scroll 2 without manual labels.
- **Hardware Tuning:** Resolved OOM issues by reducing 3D patch size to [32, 128, 128] for the RTX 4090.

---

## [2026-05-04] Day Shift: Rapid Iteration & Hyperparameter Fine-Tuning

**Status:** ACTIVE

### Purpose
Transition back to Day Shift rapid (15m) iteration cycles to explore hyperparameter space more broadly, building on the Night Shift's generalization gains.

### Strategy & Hypotheses
*   **Hypothesis:** The model has gained stable topological performance; now focus on fine-tuning learning rates and augmentation strategies to push `avg_centerline_dice` above 0.2.
*   **Cycles:** 15-minute cycles for broad hyperparameter exploration.

### Key Tweaks
*   [ ] Revert to 15-minute training budget.
*   [ ] Focus on hyperparameter pruning based on Night Shift findings.

### Outcomes & Insights
*(To be populated)*

---

## [2026-05-03] Night Shift: Long-Horizon Generalization Exploration
...

**Status:** ACTIVE

### Purpose
Transition from Day Shift rapid (15m) iteration to Night Shift sustained (1h) training cycles to improve cross-fragment generalization (Fr47 -> Fr143).

### Strategy & Hypotheses
*   **Hypothesis:** The model has successfully broken the 0.0 Dice barrier; now it needs more sustained gradient exposure to refine ink features on the validation fragment.
*   **Cycles:** 1-hour cycles focusing on architecture stability and hyperparameter tuning.

### Key Tweaks
*   [ ] Increase training budget to 3600s.
*   [ ] Keep ink-aware sampling and threshold search enabled.

### Outcomes & Insights
*(To be populated)*

---

## [2026-05-03] Day Shift: Baseline Recovery & Pipeline Audit
...

**Status:** ACTIVE

### Purpose
Investigate and resolve the "Zero-Dice" validation wall encountered during the recent Night Shift. Re-establish a stable `best_model.pt` and ensure the `villa` prize gates are correctly calibrated for early-stage autonomous exploration.

### Strategy & Hypotheses
*   **Hypothesis 1:** The model is failing to generalize from Fragment 47 to Fragment 143 due to divergent noise distributions or label styles, requiring stronger domain randomization.
*   **Hypothesis 2:** The `enforce_prize_gates` logic is prematurely rejecting models that are learning but haven't yet passed the topological thresholds (0.01 centerline Dice).
*   **Hypothesis 3:** A regression in `vesuvius_loader.py` or `train.py` (e.g., normalization or augmentation) is breaking the link between CT features and ink labels.

### Key Tweaks
*   [ ] Run "Overfit Test": Train and validate on the same fragment (Fr 47) to confirm the model *can* learn the local mapping.
*   [ ] Temporal Slice Check: Verify that the 8-layer buffer in `vesuvius_loader.py` is correctly aligned with the `num_layers` expected by the model.
*   [ ] Gate Relaxation: Temporarily disable `enforce_prize_gates` to see if `val_bpb` improves monotonically even without meeting prize-readiness criteria.

### Outcomes & Insights
*(To be populated)*

---

## [2026-05-01] Day Shift: Villa Strategy & Search Initialization (v2.7.0)


**Status:** ACTIVE

### Purpose
Align project with official `ScrollPrize/villa` strategies to maximize prize competitiveness. Focus on "Non-Metal" ink signal generalization and efficient data access.

### Key Achievements
1.  **Scroll 2/3 Search Queue:** Built and ranked a candidate queue of 110 regions in `PHerc0125` (Scroll 2) and `PHerc0332` (Scroll 3) for the First Letters/Title Prizes. Top priority: `Scroll 2 div_90`.
2.  **"Non-Metal" Model Strategy:** Initiated training of a model focused on physical features (Structure Tensors + 3D Ridges) to move beyond metal-rich contrast dependencies.
3.  **Vesuvius-C Wrapper Enhancement:** Updated `vesuvius_c_wrapper` to support the official `Volume` API from `vesuvius-c`. It now supports remote fetching/caching of Zarr chunks from `dl.ash2txt.org` directly into Python, enabling "data-on-demand" workflows.

### Configuration
*   **Model:** `GatedUNet` with `use_ridges=True` and `loss_st=0.2`.
*   **Data:** Fragments 1 & 2 pooled.
*   **Search Target:** Scroll 2 Divisions (90, 100).

### Outcomes & Insights
- Verified `Vesuvius-C` wrapper can load local data via `file://` URLs, satisfying the official library's metadata requirements while maintaining C-speed performance.
- Search queue prioritized Scroll 2 due to its higher probability of containing legible non-metal ink signatures.

---

## [Future Entry Template]
