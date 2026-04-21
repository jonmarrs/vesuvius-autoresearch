# Vesuvius Autoresearch: Experiment Sprint Kanban

This board tracks the prioritized research trajectory for the autonomous swarm. Sprints are designed to move from fundamental calibration to prize-winning breakthroughs within a 2-month window.

## 📋 BACKLOG

### Phase 3: Signal Extraction Breakthroughs
- **[Sprint 007] Anisotropic Kernel Search**: Evolve kernels specifically biased toward the XY plane to better capture thin ink layers.
- **[Sprint 008] Loss Function Evolution**: Compare Dice Loss vs. Focal Loss vs. Tversky Loss for handling extreme class imbalance (ink is rare).
- **[Sprint 009] DINO-Pretraining Integration**: Switch from random noise pretraining to Self-Supervised pretraining on all 36 unlabeled scrolls. *(May be short-circuited by Sprint 016 if TimeSformer pretrained checkpoints prove sufficient.)*

### Phase 3b: Villa Integration (official ScrollPrize submodule)
- **[Sprint 013] Villa Metrics Suite**: Integrate `centerline_dice` and `connected_components` from `villa/segmentation/evaluation/metrics/` into every autoresearch validation cycle (~10ms each) for topologically-aware model selection. Reserve `critical_components[_multiclass]` (~100ms) for checkpoint-time scoring only. Track alongside `val_bpb` in `results.tsv` so the loop can optimize against multiple prize-relevant signals.
- **[Sprint 014] Unblock Villa Label Hole Filling**: Install `opencv-python-headless`, `alphashape`, and `shapely` in the project venv so `villa/vesuvius/src/vesuvius/scripts/fill_inner_outer_labels.py` runs cleanly instead of hitting our graceful fallback. Regenerate `inklabels_filled.png` for all six labeled fragments. **Schedule outside a live shift** — changing underlying labels mid-shift would invalidate in-flight `val_bpb` comparisons against `best_model.pt`.
- **[Sprint 015] Port Villa Albumentations Recipe**: Replace our hand-rolled augmentations with the battle-tested `villa/ink-detection/train_timesformer_og.py` Albumentations pipeline (HorizontalFlip, VerticalFlip, RandomBrightnessContrast p=0.75, ShiftScaleRotate rotate=360° / shift=0.15 / scale=0.15, GaussNoise/Blur/MotionBlur p=0.4, CoarseDropout max_width=0.2·size). Tuned by the Grand Prize team for Scroll 2's noise profile; subsumes and sharpens the original Sprint 006 goal.
- **[Sprint 016] Official Vesuvius Package Migration**: Replace `vesuvius_loader.py` with `villa/vesuvius/src/vesuvius/data/{Volume,VCDataset}`. Gains: `skip_empty_patches=True`, configurable `normalization_scheme` (z-score matches Grand Prize preprocessing), multi-resolution support, and seamless `dl.ash2txt.org` / local fallback. Likely requires re-downloading fragments in OME-Zarr format.
- **[Sprint 017] TimeSformer + ResNet3D + I3D Backbone Port**: Add the three Grand Prize-winning architectures from `villa/ink-detection/` (`train_timesformer_og.py`, `64x64_256stride_i3d.py`, ResNet3D-101 pretrained) as selectable backbones in `ExperimentConfig` so the autoresearch loop can evolve across them. Download pretrained checkpoints from the ink-detection Google Drive. Feeds directly into Sprint 012's Voter Swarm.
- **[Sprint 018] Iterative Pseudo-Labeling Loop (Farritor/Nader Recipe)**: Implement the prize-winning iterative label expansion: train → predict on unlabeled regions of Scrolls 1-3 → retain pixels above τ≈0.85 confidence → mask out manual-label overlap → retrain. Target ~15 rounds on `div_100` regions. Expands our effective training set 10-100× without manual annotation; pairs directly with Sprint 011 (First Title).

### Phase 4: The Prize Run (Grand Prize & Colophons)
- **[Sprint 010] Scroll 2 "First Letters" Hunt**: Dedicated 48-hour exhaust search on Scroll 2 (PHerc0125) divisions.
- **[Sprint 011] Colophon "First Title" Search**: Targeted inner-core scanning of Scrolls 1, 2, and 3 (`div_100`). *Best run after Sprint 018 has generated pseudo-labels for the colophon region.*
- **[Sprint 012] Multi-Model Ensemble Voting**: Deploying a "Voter Swarm" of top architectures to eliminate hallucinations in discovery images. *Architectures sourced from Sprint 017.*

---

## 📅 TODO (Upcoming Weeks)

### Phase 2: Hardware Optimization (4090 Max-Out)
- **[Sprint 004] 24GB VRAM Saturation**: Automate search for the largest possible `patch_size` and `batch_size` the 4090 can handle without OOM.
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
| **Week 5** | Villa Backbone Ensemble | TimeSformer + ResNet3D + I3D voting deployed (Sprints 016-017) |
| **Week 6** | Pseudo-Label Scale-Up | >50,000 pseudo-labels retained at τ=0.85 (Sprint 018) |
| **Week 7** | **First Title Submission** | Colophon legible in Scroll 1-3 `div_100`; submission package with scale bar + 3D metadata |
