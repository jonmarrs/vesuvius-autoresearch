# Vesuvius Autoresearch: Experiment Sprint Kanban

This board tracks the prioritized research trajectory for the autonomous swarm. Sprints are designed to move from fundamental calibration to prize-winning breakthroughs within a 2-month window.

## 📋 BACKLOG

### Phase 3: Signal Extraction Breakthroughs
- **[Sprint 007] Anisotropic Kernel Search**: Evolve kernels specifically biased toward the XY plane to better capture thin ink layers.
- **[Sprint 008] Loss Function Evolution**: Compare Dice Loss vs. Focal Loss vs. Tversky Loss for handling extreme class imbalance (ink is rare).
- **[Sprint 009] DINO-Pretraining Integration**: Switch from random noise pretraining to Self-Supervised pretraining on all 36 unlabeled scrolls.

### Phase 4: The Prize Run (Grand Prize & Colophons)
- **[Sprint 010] Scroll 2 "First Letters" Hunt**: Dedicated 48-hour exhaust search on Scroll 2 (PHerc0125) divisions.
- **[Sprint 011] Colophon "First Title" Search**: Targeted inner-core scanning of Scrolls 1, 2, and 3 (`div_100`).
- **[Sprint 012] Multi-Model Ensemble Voting**: Deploying a "Voter Swarm" of top architectures to eliminate hallucinations in discovery images.

---

## 📅 TODO (Upcoming Weeks)

### Phase 2: Hardware Optimization (4090 Max-Out)
- **[Sprint 004] 24GB VRAM Saturation**: Automate search for the largest possible `patch_size` and `batch_size` the 4090 can handle without OOM.
- **[Sprint 005] High-Resolution 3D Depth**: Increasing `num_layers` from 16 to 48 to capture deeper structural context.
- **[Sprint 006] Domain Randomization Swarm**: Autoresearch the optimal augmentation parameters (rotation, scale, elastic warp) to prevent memorization of Fragment 1.

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
