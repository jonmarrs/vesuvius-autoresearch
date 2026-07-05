# bountyhunter: Vesuvius Autoresearch

![teaser](progress.png)

*The first autonomous research swarm for the Vesuvius Challenge.*

> **Honest results, methodology, and negative results:** see [FINDINGS.md](FINDINGS.md). Current headlines: a **working, window-compliant ink detector** (held-out same-scroll `val_f1` 0.393 / prevalence-lift 2.07, [reproduction](reports/detector/REPRODUCTION.md)), the **first valid cross-scroll measurement** (lift 1.29 — the quantified generalization gap), a **SOTA-distilled model** (`val_f1` 0.662 / lift 3.24 *agreement-with-teacher* on the open SOTA data, [report](reports/detector/sota_distill_measurement.md)), and **measured cross-scroll distillation**: training-scroll diversity lifts unseen-scroll transfer 1.22 → 2.12 at fixed budget, then saturates at ≈2.1 with a third scroll ([diversity](reports/detector/cross_scroll_distill.md), [scaling](reports/detector/cross_scroll_scale.md)). An earlier "the 64 px window is learnability-limited" reading was corrected: the window costs *legibility*, not detectability — see FINDINGS.
> **Live experiment tracking:** [wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch).

`bountyhunter` is an experiment in having AI agents perform their own end-to-end computer vision research. It automates the cycle of hypothesis generation, hyperparameter optimization, model training, and performance evaluation to uncover the "Gold Standard" configurations for reading ancient carbonized scrolls.

## 🚀 Key Features

- **Working ink detector** (`vesuvius_autoresearch.detector`): the proven 2023 Grand-Prize TimeSformer recipe, productionized and tested, with a one-command `reproduce`. (A full-resolution ResEncUNet alternative was built and *underperformed* it under our recipe — documented, not discarded.)
- **Honest metric contract** (`detector/metrics.py` + `measure` CLI): threshold-swept F1 primary; average precision + AP-prevalence-lift as imbalance-robust gates; ROC-AUC secondary. The inherited `skeleton_distance_length` "prize gate" was **removed after we proved it invalid** (location-blind; probe included).
- **SOTA open-data tooling + distillation** (`repro/sota_data/`): anonymous-S3 access to `s3://vesuvius-challenge-open-data/`, OME-Zarr extraction, and a teacher–student distillation pipeline onto the newly-open SOTA surface volumes.
- **Autonomous Research Loop:** samples a multidimensional configuration space (architectures, loss functions, augmentations) under fixed time budgets, with per-cycle preflight gates.
- **On-the-fly Multi-tasking:** real-time 3D Structure Tensor and Ridge Map computation for rich structural supervision.
- **Calibration Baselines:** periodic re-evaluation against the fixed 2023 Grand Prize recipe to prevent research drift.

## Quick start

**Requirements:** A single NVIDIA GPU (tested on RTX 4090/H100), Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Download data (~5 min)
uv run python scripts/archive/download_data.py --fragment 4

# 4. Run a single training smoke test (~30 s) to verify your setup
PYTHONPATH=. uv run python scripts/training/train.py --test

# 5. Kick off the autonomous research loop
./start.sh        # wraps: uv run python run_autoresearch_loop.py
./stop.sh         # graceful shutdown
```

## Running the agent

Spin up your coding agent of choice in this repo, then prompt something like:

```
Hi, have a look at docs/program.md and let's kick off a new experiment!
```

The `program.md` file is essentially a super lightweight "skill".

## 📈 Tracking progress

- **`history.tsv`**: Every evaluated cycle — `val_bpb`, topology metrics (`avg_skel_dist`, `avg_centerline_dice`), throughput, and the full config JSON.
- **`results.tsv`**: Experiments that beat the then-current baseline.
- **`prize_readiness.tsv`**: Per-cycle check of the model against prize submission gates.
- **`docs/LAB_NOTEBOOK.md`**: High-level strategic record of research milestones.
- **`sprint_logs/`**: Detailed per-shift execution traces and config samples.

## ✅ Validation

Use the project interpreter for tests; a system `pytest` may not have the GPU/CT
dependencies installed.

```bash
uv run python scripts/run_validation_tests.py
```

For prize-submission mechanics specifically:

```bash
uv run python scripts/build_scroll23_search_queue.py
uv run python scripts/rank_scroll23_candidates.py
uv run python scripts/run_ranked_inference.py
uv run python scripts/generate_submission_package.py
uv run python scripts/validate_prize_artifact.py --metadata submission_package_dry_run/metadata.json
```

## 🔬 Evidence & upstream contributions

- **GPU fiber/ridge detection for villa** ([ScrollPrize/villa#1033](https://github.com/ScrollPrize/villa/pull/1033)): closed-form 3×3 eigensolver replacing the cuSolver path that fails past ~64³, with tiled/halo execution (512³ in ~1 GB VRAM) and tiled-vs-dense parity tests. Validation details in [`reports/fibers_gpu_validation_2026-06.md`](reports/fibers_gpu_validation_2026-06.md).
- **Real-scroll runs:** vesselness on a 256³ PHerc0332 region in ~1.2 s — [contact sheet](reports/real_scroll_evidence/vesselness_contact_sheet.png), plus Scroll 2/3 candidate evidence under [`reports/scroll23_evidence/`](reports/scroll23_evidence/).
- **Optimized inference (Primus/LeJEPA loader):** diagnostics in [`reports/primus_optimized_inference_validation_2026-06.md`](reports/primus_optimized_inference_validation_2026-06.md).
- **Hallucination mitigation:** methodology in [`submission_package_dry_run/HALLUCINATION_MITIGATION.md`](submission_package_dry_run/HALLUCINATION_MITIGATION.md).

## Project structure

```
src/vesuvius_autoresearch/detector/ — the productionized ink detector (train/infer/eval/metrics/measure CLI)
repro/sota_data/         — SOTA open-data tooling: S3 discover/fetch, OME-Zarr convert, distillation pipeline
repro/gp_winner/, repro/ink_segformer/ — replication studies (2023 GP recipe; 224px SegFormer)
run_autoresearch_loop.py — autonomous experimentation manager (day/night shifts)
scripts/training/train.py — the loop's training and evaluation
src/vesuvius_autoresearch/core/vesuvius_loader.py — data loading, ridge computation
src/vesuvius_autoresearch/fibers/ — GPU fiber/ridge/vesselness detection
vesuvius_model.py        — the loop's architecture zoo (ResEnc-UNet, GatedUNet, TimeSformer, ...)
scroll_augmentations.py  — scroll-specific augmentations (decohesion, squeeze, z-dropout, ...)
scripts/                 — inference, labeling, evaluation, and prize-packaging tools
docs/program.md          — agent instructions
pyproject.toml           — dependencies
```

## Design choices

- **Autonomous Tweak Families.** The loop script (`run_autoresearch_loop.py`) intelligently samples from different "families" of tweaks (LR, Architecture, Loss Balance) based on recent success.
- **Fixed Time Budget.** Training runs for a fixed wall-clock budget (default 15 mins for Day Shift, 60 mins for Night Shift). This ensures experiments are comparable and the agent optimizes for the best model *within the available compute*.
- **Multi-task Supervision.** Models are trained not just on ink labels, but also on auxiliary tasks like 3D ridge detection and structure tensor alignment to improve generalization.

## GPU fiber detection

`vesuvius_autoresearch.fibers` is a standalone GPU fiber/ridge/vesselness
detector with a closed-form symmetric-3×3 eigensolver that avoids the cuSolver
`eigvalsh` failure on large Hessian batches (14–94× over NumPy; 512³ tiled in
~1 GB VRAM). See **[docs/FIBER_DETECTION.md](docs/FIBER_DETECTION.md)**.

## Scroll-specific augmentations

`scroll_augmentations.py` is a standalone, dependency-light library of nine
GPU-native augmentations that model scroll-CT artifacts (beam scatter,
compression, missing slices, Rician noise, …) for ink-detection training —
addressing [villa issue #201](https://github.com/ScrollPrize/villa/issues/201).
The training loop uses it directly. See **[docs/SCROLL_AUGMENTATIONS.md](docs/SCROLL_AUGMENTATIONS.md)**
for the per-family reference, usage, and the [before/after demo](reports/augmentation_demos/all_families.png).

## License

MIT
