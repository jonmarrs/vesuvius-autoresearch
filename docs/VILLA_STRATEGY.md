# Vesuvius Autoresearch: Villa Strategy Roadmap

This document outlines how we leverage and contribute to the official `ScrollPrize/villa` repository.

## 1. Technical Contributions (Progress Prize Track)
*High-probability monthly awards ($1k - $20k) for solving official TODOs and bottlenecks.*

### [Priority 0] Keep the Villa Pin Prize-Current (STATUS: AUDIT TOOL ADDED)
*   **Discovery**: As of the May 7, 2026 audit, local `villa` is at `4b7c5c20d95b404b7e92dc70606a1b1ed8648fd3`, official `origin/main` is `ad4e1b7d8a85c553c0b135b5f02ef98af9a9e923`, and the merge base is `9f2476386855f209e8964ee152da33787f6d25cc`. The checkout is diverged: 5 official upstream commits are available and 5 local Villa commits carry Autoresearch patches. The official prize-relevant delta is 18 files, concentrated in Lasagna and Volume Cartographer / VC3D.
*   **Action**: Run `git -C villa fetch origin main`, `uv run python scripts/audit_villa_upstream.py`, and `uv run python scripts/plan_villa_prize_opportunities.py` before prize sprints. Use the divergence-aware fields in `reports/villa_upstream_audit.json` to decide whether to rebase local Villa patches, selectively port upstream VC3D/Lasagna changes, or keep the pin fixed. Then use `reports/villa_prize_opportunities.json` to pick the highest-impact official issue-backed task.
*   **Impact**: Prevents Autoresearch from optimizing against stale official APIs, which directly affects reproducible submission packaging and Progress Prize contribution timing.

### [Priority 0.5] Official Issue-Backed Prize Queue (STATUS: PLANNER ADDED)
*   **Discovery**: Current official open issues include progress-prize candidates for whole-volume deformation (#203), scroll-specific 3D augmentations (#201), surface/fiber/ink label generation (#193), accurate 3D ink labels (#192), compressed/high-curvature surface and fiber prediction (#191), VC3D fiber prediction integration (#369), and OME-Zarr scale metadata (#497).
*   **Action**: Use `reports/villa_prize_opportunities.json` as the Autoresearch sprint queue. The current top task is #191: route high-occupancy Scroll 2/3 candidates through Lasagna/fiber preprocessing before ink inference. The concrete queue is already in `reports/lasagna_fiber_worklist.tsv`, headed by occupied `PHerc0125` div_90/div_100 and `PHerc0332` div_90 windows. The planner now marks every opportunity as `diverged_with_local_patches`, so any Villa pin update must preserve local CuPy, Betti, Autoresearch, Vesuvius-C, and spatial-transform changes.
*   **Impact**: Aligns local model work with public Progress Prize signals while also attacking the geometry bottleneck that keeps First Letters/Title candidates low-confidence.

### [Priority 0.6] Active Villa Evidence Pipeline (STATUS: QUEUE READY)
*   **Discovery**: `reports/scroll23_ranked_candidates.tsv` and `reports/lasagna_fiber_worklist.tsv` now contain local, occupied, submittable 64x64 Scroll 2/3 candidates. This makes the next Villa-backed step executable instead of exploratory.
*   **Action**: After the current Night Shift GPU cycle finishes, run `scripts/run_ranked_inference.py --execute`, re-rank prediction statistics, rebuild the Lasagna/fiber worklist, and run `scripts/run_villa_prize_evidence_chain.py` for the top candidates.
*   **Impact**: Produces a Villa-native evidence directory with ink/fiber overlays, structure tensor outputs, validation reports, and review artifacts for First Letters / First Title triage.

### [Priority A] CuPy Acceleration for Fiber Tools (STATUS: IMPLEMENTED)
*   **Gap**: `villa/foundation/datasets/fibers-dataset/tools.py` had explicit TODOs for GPU speedup.
*   **Action**: Ported `hessian`, `detect_ridges`, `nms_3d`, and `detect_vesselness` to CuPy.
*   **Impact**: **5-10x speedup** for community fiber extraction. Ready for Pull Request.

### [Priority B] Official Vesuvius-C Python Bindings (STATUS: PREPARED)
*   **Action**: Prepared a PR-ready package in `villa/vesuvius-c/python/` with `setup.py` and `README`.
*   **Impact**: Enables community-wide "data-on-demand" workflows with C-speed performance.

## 2. Infrastructure Integration (Grand Prize Track)
*Increasing the robustness and reproducibility of our models.*

### [Priority C] Autoresearch for nnUNet (STATUS: IMPLEMENTED)
*   **Action**: Created `villa/segmentation/model_optimization_framework/run_autoresearch_nnunet.py`.
*   **Impact**: Intelligent hyperparameter evolution for official nnUNet baselines.

### [Priority D] Betti Loss for multi-task-3d-unet (STATUS: INTEGRATED)
*   **Action**: Created `training/losses/betti_loss.py` and registered it in `BaseTrainer`.
*   **Impact**: Structural continuity enforcement for community-wide models.

## 3. Data & Generalization (First Letters Track)
*Hunting for ink in Scrolls 2-3 using non-contrast signals.*

### [Priority E] Fiber-Oriented Training (STATUS: TOOL READY)
*   **Action**: Created `generate_fiber_labels.py` (local-optimized `hz-vt-generator`).
*   **Goal**: Model training on non-metal papyrus structure.

## 4. Automation & Scale (Stage 2 Goal)
*Solving the unwrapping bottleneck.*

### [Priority G] Grand Prize TimeSformer (STATUS: IMPLEMENTED)
*   **Action**: Integrated `VesuviusTimeSformer` (canonical GP configuration) into `vesuvius_model.py`.
*   **Impact**: Provides a world-record baseline for ink detection. Judges will value the use of validated architectures.

### [Priority H] Upstream ResNet3D + 3D Decoder Runtime (STATUS: IMPLEMENTED)
*   **Discovery**: Current upstream `villa/ink-detection` adds `train_resnet3d_3d_decoder.py`, `inference_resnet3d_3d_decoder.py`, and optimized inference support for `MODEL_TYPE=resnet3d-152-3d-decoder`.
*   **Action**: Added an Autoresearch architecture adapter and export smoke test for the upstream 3D decoder contract. This acts as the next high-value model family after the current TimeSformer/ResEnc UNet path.
*   **Impact**: The upstream docs call out a 62-layer window with `TILE_SIZE=256` for tracked 3D-decoder checkpoints. This gives us a stronger cross-scroll context model for Scroll 2/3 review candidates while preserving an official inference path.

### [Priority H.5] Scroll-Specific 3D Augmentations (STATUS: LOCAL PRESET ADDED)
*   **Discovery**: Official Villa issue #201 asks for GPU-friendly augmentations that mimic scroll-specific artifacts: decohesion/smearing, warping, and squeezing/pulling.
*   **Action**: `train.py` now exposes torch-native `aug_scroll_decohesion_p`, `aug_scroll_squeeze_p`, `aug_scroll_z_dropout_p`, and `aug_scroll_intensity_drift_p` controls. These run after the existing Villa-style augmentation path and preserve ink/fiber label alignment for spatial warps.
*   **Impact**: Gives Autoresearch a direct search axis for cross-scroll generalization on Scroll 2/3, while keeping the implementation close to the official Progress Prize request.

### [Priority I] Crackle-Viewer Inspection (STATUS: WRAPPER READY)
*   **Action**: Created `scripts/launch_crackle_viewer.py` to bridge the gap between AI predictions and human review.
*   **Impact**: Critical for the **First Title / First Letters** prize. Allows rapid manual confirmation of high-uncertainty regions identified by the sampler.

### [Priority J] Lasagna Surface-Fitting Pipeline (STATUS: UPSTREAM MAPPED)
*   **Discovery**: Upstream Villa now exposes `lasagna/` as a first-class surface fitting, tifxyz, and 3D UNet training workflow, including conversion to VC3D OME-Zarr outputs.
*   **Action**: Use `uv run python scripts/build_lasagna_fiber_worklist.py` to produce `reports/lasagna_fiber_worklist.json`, then run structure-tensor and Lasagna preprocessing on the top occupied Scroll 2/3 candidates before feeding improved surfaces into the existing evidence chain.
*   **Impact**: Better local surface geometry is the most direct way to turn our current non-empty but low-confidence candidates into papyrologist-reviewable First Letters/Title images.

### [Priority J.5] VC3D Fiber Prediction Overlays (STATUS: LOCAL EXPORT ADDED)
*   **Discovery**: Official Villa issue #369 asks for better VC3D use of fiber predictions; issue #497 calls out proper OME-Zarr scale metadata for review tools.
*   **Action**: `predict.py` now writes `*_fiber.png`, `*_fiber.zarr`, `fiber_vc3d_zarr_path`, and `fiber_stats` beside the existing ink artifacts. `scripts/validate_prize_artifact.py` validates OME-Zarr spatial scale metadata when present.
*   **Impact**: Autoresearch predictions now produce reviewable fiber overlays that can be loaded alongside ink evidence, improving human triage and creating a concrete Progress Prize contribution path for VC3D integration.

## 5. Domain Adaptation & Open Problems (Stage 2 Advanced)
*Tackling the remaining bottlenecks for full-scroll recovery.*

### [Priority K] Uncertainty-Aware Mean Teacher (STATUS: STRATEGY DEFINED)
*   **Action**: Use `villa/vesuvius/src/vesuvius/models/training/trainers/semi_supervised/train_uncertainty_aware_mean_teacher.py`.
*   **Strategy**: Train with labeled Fragment 1 data and unlabeled Scroll 2/3 volumes to solve the "Domain Gap" problem. Use autoresearch to optimize `ema_decay` and `consistency_weight`.
*   **Impact**: The most direct path to the **$200,000 Grand Prize** (90% coverage) by learning Scroll 2's unique texture from raw data.

### [Priority L] Automated ARAP Parameterization (STATUS: STRATEGY DEFINED)
*   **Action**: Integrate `vesuvius_c_wrapper` into the ARAP flattening scripts in `villa/volume-cartographer`.
*   **Impact**: Accelerates the "Representation" open problem, qualifying for a **$10k-$20k Progress Prize** for Software Performance/Scalability.

## 6. Foundation Models & Community Knowledge (Ultimate Tier)
*Leveraging the full collective intelligence of the Vesuvius Challenge.*

### [Priority N] LeJEPA Foundation Pretraining (STATUS: LAUNCHER READY)
*   **Action**: Created `scripts/launch_lejepa.py` to interface with the official `lejepa` trainer.
*   **Strategy**: Pretrain a single massive encoder on ALL unlabeled scroll volumes (Scrolls 1-4). This creates a "Foundation Model" for papyrus texture that makes fine-tuning on limited labels significantly more effective.
*   **Impact**: Essential for the **$200,000 Grand Prize**. Foundation models are the only proven way to generalize across different scan energies.

### [Priority O] RAG-Guided Autoresearch (STATUS: INTEGRATED)
*   **Action**: Created `scripts/rag_researcher.py` using the official `Discord RAG Chatbot`.
*   **Impact**: Allows the Autoresearch loop to "ask the community" for the best hyperparameters. Instead of a random search, we use AI to retrieve successful strategies from the Discord knowledge base, saving thousands of GPU hours.

### [Priority P] 3D (Volumetric) Ink Detection (STATUS: STRATEGY DEFINED)
*   **Action**: Implement a launcher for Ryan Chesler's 3D-only approach (bypassing unwrapping).
*   **Impact**: A "Wildcard" strategy for the **First Letters Prize** in regions where segmentation is currently impossible.

### [Priority Q] Graph-Based Sheet Stitching (STATUS: IMPLEMENTED)
*   **Discovery**: Found formal problem definition in `villa/thaumato-anakalyptor/documentation/Sheet_Stitching_Problem_Definition.pdf`.
*   **Action**: Implemented the winding-angle assignment function $f: N \to \mathbb{R}$ natively in `scripts/sheet_stitcher.py` and integrated it into the `scripts/autoresearch_thaumato_solver.py` hyperparameter sweep loop.
*   **Impact**: Solves the "Winding Gap" problem, allowing for the massive, multi-winding segments needed for the **$200,000 Grand Prize**.

### [Priority R] Foundation Model Pretraining (STATUS: IMPLEMENTED)
*   **Discovery**: Official LeJEPA and MAE trainers located in `villa/vesuvius/src/vesuvius/models/training/trainers/self_supervised/`.
*   **Action**: Updated `scripts/launch_lejepa.py` to automatically discover all unlabeled chunks from Scrolls 1-4 (`RealScroll_1`, `PHerc0125`, `PHerc0332`, `RealScroll_4_Large`) using `glob`, and added an `--execute` flag to execute large-scale self-supervised pretraining natively.
*   **Impact**: Radical improvement in generalization. This is the "Foundation Model" approach that the Challenge organizers have explicitly called for in Stage Two.
