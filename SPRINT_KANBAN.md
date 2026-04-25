# Vesuvius Autoresearch: Experiment Sprint Kanban

This board tracks the prioritized research trajectory for the autonomous swarm. Sprints are designed to move from fundamental calibration to prize-winning breakthroughs within a 2-month window.

## 📋 BACKLOG

### Phase 3: Signal Extraction Breakthroughs
- **[Sprint 007] Anisotropic Kernel Search**: Evolve kernels specifically biased toward the XY plane to better capture thin ink layers.
- **[Sprint 008] Loss Function Evolution**: Compare Dice Loss vs. Focal Loss vs. Tversky Loss for handling extreme class imbalance (ink is rare).
- **[Sprint 009] DINO-Pretraining Integration**: Switch from random noise pretraining to Self-Supervised pretraining on all 36 unlabeled scrolls. *(Likely short-circuited by Sprint 019 — LeJEPA is the 2024 successor to DINO and already implemented in villa. Keep as fallback if LeJEPA fails to converge on our fragment sizes.)*

### Phase 3b: Villa Integration (official ScrollPrize submodule)
- **[Sprint 013] Villa Metrics Suite**: (DONE in `train.py`)
- **[Sprint 014] Unblock Villa Label Hole Filling**: (DONE)
- **[Sprint 015] Port Villa Albumentations Recipe**: (DONE in `train.py`)
- **[Sprint 016] Official Vesuvius Package Migration**: (DONE) Replaced `vesuvius_loader.py` backend with `villa/vesuvius/src/vesuvius/data/Volume`. Converted local TIF stacks to OME-Zarr for robust, high-performance loading and official normalization.
- **[Sprint 017] TimeSformer + ResNet3D + I3D Backbone Port**: (DONE in `train.py`)
- **[Sprint 018] Iterative Pseudo-Labeling Loop (Farritor/Nader Recipe)**: Implement the prize-winning iterative label expansion: train → predict on unlabeled regions of Scrolls 1-3 → retain pixels above τ≈0.85 confidence → mask out manual-label overlap → retrain. Target ~15 rounds on `div_100` regions.
- **[Sprint 019] LeJEPA Self-Supervised Pretraining**: (ACTIVE) Fully implemented `VesuviusTrainer` with `SIGRegLoss` for representation learning on unlabeled scrolls.
- **[Sprint 020] Uncertainty-Aware Mean Teacher for Pseudo-Labels**: (ACTIVE) Integrated `TwoStreamBatchSampler` and EMA teacher logic into `VesuviusTrainer` for semi-supervised label expansion.
- **[Sprint 021] ResEnc UNet Backbone Port**: (DONE in `train.py`)
- **[Sprint 022] Fixed GP-Winner Baseline in the Swarm**: (DONE in `run_autoresearch_loop.py`)
- **[Sprint 023] Structure-Tensor Auxiliary Task**: (DONE in `train.py`)
- **[BUGFIX] (DONE)** Resolved device mismatch in `SpatialTransform` and numerical gradient error in `vesuvius_loader.py`.

### Phase 3c: Augmentation & Data Pipeline
- **[Sprint 028] 3D-Native Augmentations (batchgeneratorsv2)**: (DONE in `train.py`)
- **[Sprint 029] ThaumatoAnakalyptor Auto-Segmentation**: (DONE) Deploy `villa/thaumato-anakalyptor` via the `scripts/launch_thaumato.py` wrapper to automatically generate high-precision 3D segmentations from Scroll 2 (PHerc0125). Expanding our training set by 10x with these automatically unrolled sheets is critical for the First Letters Prize.
- **[Sprint 030] Crackle Viewer Visual Verification**: (DONE) Integrate `villa/crackle-viewer` via the `scripts/launch_crackle_viewer.py` wrapper. This GUI enables fast, human-in-the-loop qualitative validation of ink predictions, ensuring our "val_bpb" improvements translate to papyrologically plausible strokes before we submit.
- **[Sprint 031] SAM2-Photogrammetry 3D Ground Truth**: (DONE) Use `villa/sam2-photogrammetry` to extract geometric ground truth from raw photogrammetry captures. This will be used to heavily penalize model hallucinations that appear off the physical papyrus surface.

### Phase 4: The Prize Run (Grand Prize & Colophons)
- **[Sprint 010] Scroll 2 "First Letters" Hunt**: Dedicated 48-hour exhaust search on Scroll 2 (PHerc0125) divisions. *Operationalized by Sprint 026 (submission-package checklist).*
- **[Sprint 011] Colophon "First Title" Search**: Targeted inner-core scanning of Scrolls 1, 2, and 3 (`div_100`). *Best run after Sprint 020 (UA-MT) or Sprint 018 (fallback) has generated pseudo-labels for the colophon region.*
- **[Sprint 012] Multi-Model Ensemble Voting**: Deploying a "Voter Swarm" of top architectures to eliminate hallucinations in discovery images. *Architectures sourced from Sprints 017 + 021.*
- **[Sprint 024] Package Autoresearch Loop as Progress Prize Submission**: (DONE) Target the next monthly Progress Prize tranche (deadline **2026-04-30 11:59pm PT** per `villa/scrollprize.org/docs/34_prizes.md`). Submission tiers: Papyrus $1k / Sestertius $2.5k / Denarius $10k / Gold Aureus $20k. Package includes: (a) clean README with setup + one-command run, (b) short walkthrough video showing a cycle, (c) licensing under permissive terms, (d) a `results.tsv` artifact + `best_model.pt` on HuggingFace showing the loop beats a fixed baseline, (e) explicit cross-links to the villa components we build on (metrics, Albumentations, and whichever Phase 3b sprints have landed). Judges favor tools that "actually get used" — ship early and solicit community feedback. Low technical risk, highest near-term expected return on hours invested.
- **[Sprint 026] First Letters Submission Package Dry-Run**: (DONE) Before Sprint 010 burns GPU cycles on a blind hunt, build the submission package end-to-end on a known-positive Fragment 1 / Fragment 5 region to verify every checklist item clears review: (a) single static discovery image, (b) **scale bar showing 1 cm**, (c) segmentation ID or 3D position metadata, (d) window size ≤ 64×64 px at 8 µm (Sprint 004 cap) — verified programmatically before image export, (e) explicit train/predict mask showing zero overlap, (f) Docker image or clear human-in-the-loop instructions, (g) a written "Hallucination Mitigation" note referencing our ensemble (Sprint 012) + per-pixel confidence (Sprint 020) + villa `centerline_dice` / `cc_diff` metrics (Sprint 013) as evidence the strokes are real. Produces a submission template reusable for Scrolls 2-3 proper.
- **[Sprint 025] VC3D / Villa Progress Prize Contributions** *(optional, lower ROI)*: Pick off tagged issues from `github.com/ScrollPrize/villa/issues?label=VC3D` or `label="help wanted"`. Mostly C++ / Qt work — lower fit for this project unless we have spare cycles or want Python bindings / docs contributions to qualify for the Progress Prize. Defer unless Sprint 024 lands and we want a second monthly submission.
- **[Sprint 027] Mutex-Affinity Papyrus Sheet Instance Segmentation** *(Grand Prize track, deferred)*: Port `villa/vesuvius/src/vesuvius/models/training/trainers/mutex_affinity_trainer.py` for separating individual papyrus sheets in the 3D volume. Orthogonal to ink detection but necessary for the Grand Prize (which requires 4 passages × 140 characters, which in turn requires long contiguous segmented sheets). Large effort; defer until a First Letters / First Title submission has been banked.

---

## 📅 TODO (Upcoming Weeks)

### Phase 2: Hardware Optimization (4090 Max-Out)
- **[Sprint 004] 24GB VRAM Saturation**: Automate search for the largest possible `patch_size` and `batch_size` the 4090 can handle without OOM. ⚠️ **Prize-submission cap**: per `villa/scrollprize.org/docs/34_prizes.md`, ML outputs destined for First Letters / First Title / Grand Prize submissions must use window size ≤ 0.5×0.5 mm = **64×64 px at 8 µm**. Any evolved config with `patch_size > 64` is research-only and must be tagged non-submittable in `results.tsv` / `best_model.pt` metadata.
- **[Sprint 005] High-Resolution 3D Depth**: Increasing `num_layers` from 16 to 48 to capture deeper structural context.
- **[Sprint 006] Domain Randomization Swarm**: Autoresearch the optimal augmentation parameters (rotation, scale, elastic warp) to prevent memorization of Fragment 1. *Use the villa Albumentations recipe from Sprint 015 as the starting point, then evolve around it.*

---

## 🚀 IN PROGRESS

### Phase 1: Fundamental Grounding (Week 1)
- **[Sprint 001] Gold Standard Baseline**: (ACTIVE) Calibration of the autonomous loop against genuine Fragment 1 labels.
- **[Sprint 002] Multi-Fragment Training**: Preparing to pool Fragments 1, 2, and 5 into a single training source.
- **[Sprint 003] Denoising Backbone Evolution**: Comparing GroupNorm vs. InstanceNorm for high-noise Paris scan environments.

---

## ✅ DONE
- **[Sprint 000] Foundation Initialization**: 100% Offline loader implementation and bandwidth safety checks.
- **[Sprint 000b] Data Library Setup**: Automated download of 1GB samples for 36 public scrolls and 6 labeled fragments.

---

## 📈 Weekly Milestone Targets

| Week | Milestone | Target Metric |
| :--- | :--- | :--- |
| **Week 1** | Labeled Grounding | >0.70 Dice Score (Local Cross-Fragment) |
| **Week 2** | Hardware Saturation | 100% 4090 VRAM Utilization (256x256 patches) |
| **Week 3** | Generalization Leap | >0.80 Dice Score (Scroll 1 -> Scroll 5) |
| **Week 4** | **Title Discovery Run** | First Legible Letters in Scroll 3 Core |
| **Week 5** | Villa Backbone Ensemble | TimeSformer + ResNet3D + I3D + ResEnc UNet voting deployed (Sprints 016-017, 021) |
| **Week 5.5** | **Progress Prize Submission** | Autoresearch loop packaged and submitted by 2026-04-30 (Sprint 024) |
| **Week 6** | SSL / Semi-Sup Upgrade | LeJEPA-pretrained encoder + UA-MT pseudo-label weighting online (Sprints 019, 020) |
| **Week 6.5** | GP-Baseline Calibration | Fixed `train_gp_winner` config evaluated every 10 cycles; our evolved lineage beats it on `val_bpb` (Sprint 022) |
| **Week 7** | **First Letters Dry-Run** | Full submission package validates on Fragment 1/5 with scale bar, seg ID, zero train/predict overlap, hallucination note (Sprint 026) |
| **Week 8** | **First Title Submission** | Colophon legible in Scroll 1-3 `div_100`; submission package reuses the Sprint 026 template |
