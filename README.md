# bountyhunter: Vesuvius Autoresearch

*The first autonomous research swarm for the Vesuvius Challenge.*

> **Honest results, methodology, and negative results:** see [FINDINGS.md](FINDINGS.md). Current headlines: a **working, window-compliant ink detector** (held-out same-scroll `val_f1` 0.393 / prevalence-lift 2.07, [reproduction](reports/detector/REPRODUCTION.md)), the **first valid cross-scroll measurement** (lift 1.29 — the quantified generalization gap), a **SOTA-distilled model** (`val_f1` 0.662 / lift 3.24 *agreement-with-teacher* on the open SOTA data, [report](reports/detector/sota_distill_measurement.md)), **measured cross-scroll distillation**: training-scroll diversity lifts unseen-scroll transfer 1.22 → 2.12 at fixed budget, then saturates at ≈2.1 with a third scroll ([diversity](reports/detector/cross_scroll_distill.md), [scaling](reports/detector/cross_scroll_scale.md)); and — the load-bearing result — a **ground-truth calibration** built by registering 2023 hand labels onto the SOTA flattening: against human labels the canon prediction scores ROC-AUC 0.56–0.70 (segment-dependent), and on a **held-out** segment the clean distilled students read **ROC-AUC 0.731–0.746 / lift 2.3–2.4** against an all-positive floor of 0.518 ([report](reports/detector/registered_gt_heldout_validation.md)) — genuine held-out generalization, at or just under the canon teacher's 0.753 there, so read it as faithful distillation of a teacher that *does* read rather than as beating it. **Corrected 2026-08-07:** this previously said the students read near chance; that was a hardcoded-constant bug in our own registration, found and published as a retraction ([detail](reports/detector/registration_offset_2026-08-07.md)). July: the surface renderer **gate-PASSED a second-scroll validation** (PHerc 1667 clean triple, NCC 0.78 vs pre-registered 0.60; Scroll 1's 0.59 confirmed as a resolution-mismatched comparison), rendered independent surface volumes of PHerc 1667's merged full-reading geometry (note: villa's own `vc_obj2tifxyz` + `vc_render_tifxyz` already cover both of our input paths more capably — an earlier "for the first time" framing here was wrong), and the published reading's 22 columns were registered onto that geometry as **[ScrollGT](https://github.com/jonmarrs/scrollgt)'s first non-training-scroll target** — on which our own models measure at the floor (arm C col-vs-gutter AUC 0.575 against a noise floor of 0.578 on the definitive full-band n=18v17 rows, i.e. statistically at the floor, texture not letterforms; an earlier 0.667 here came from a superseded n=3v2 extreme; [report](reports/detector/scrollgt_v02_columns.md)). Earlier over-reads (the "64 px window is learnability-limited" claim; a first over-optimistic ground-truth framing) were caught and corrected — see FINDINGS.
> **Current track (Sept 2026) — spiral fitting.** villa deprecated `ink-detection/` in late August, so
> active work moved to `spiral-fitting/`. Headline: villa's loop optimises recovered ink
> (`total_fg_pixels`) with a geometry cross-check (`satisfied_area`), and we have **four
> pre-registered cases where those move independently** — a config change that improved geometry
> +1.03% while costing **-10.35% of the ink** (n=12), two refits that raised geometry **+17.66% and
> +16.24% for no ink gain at all**, and an ablation of **5,413 winding constraints** that measurably
> *degraded* the geometry (-0.69%, p=0.0027) while reading held. The fourth bears on strategy:
> winding constraints are what villa names as the fastest path to unrolling at scale. The second answers an avenue villa names in its open
> problems ("automatically crop 'good' regions of the spiral fit... as surface patch inputs to a
> subsequent run") with a **registered FAILURE — twice**, the second study built to rule out the
> obvious confound in the first and designed while the first's results were still unread. Both
> geometry gains are **circular by construction** — the arm is selected on satisfaction and then
> scored on it — which is exactly why a loop using that guard would read either as success; and both
> ink nulls are bounded at ~10%, not zero. **All of it measured on villa-spiral `6847063f`;
> current villa recovers 67.6% more ink through a byte-identical scorer, so these describe
> superseded code. Re-measured 2026-09-12 and the extension FAILED: on current code the ink null
> reproduces but the geometry evidence does not, so the decoupling is a claim about `6847063f`
> alone.** Detail:
> [SPIRAL_FINDINGS_SUMMARY.md](reports/SPIRAL_FINDINGS_SUMMARY.md),
> [verdict](reports/patch_bootstrap_verdict.md). Runs on one consumer GPU from published artifacts.
> **Sept 19-22 — where the noise actually lives, and one part of it is switchable.** The lasagna
> flatten is a **stochastic optimiser**: two renders of byte-identical meshes, one pinned tree,
> byte-identical code, lay the **same surface** out on grids offset ~7 voxels in-plane (0.25 vx apart
> along the normal — [correction](reports/the_flatten_moves_the_grid_not_the_surface.md)) and move
> `total_fg_pixels` **3.04%**.
> It has no RNG to seed — the cause is CUDA reduction order alone — and asking PyTorch for
> deterministic algorithms makes it **bit-reproducible** (identical `x/y/z.tif` by md5) at a 9.5×
> flatten cost, ~11 min against 2 h renders
> ([measurement](reports/the_flatten_is_reproducible_when_asked.md)). That collapses the floor for
> studies manipulating **one fixed surface** from 3.04% to **0.0014%** — 24 pixels — which is what
> made a controlled result possible: displacing the flattened surface **4 voxels** costs ink in
> **both** directions, −19.77% inward and −4.48% outward, so the fitted surface sits near a local
> maximum, steep inside and shallow outside
> ([report](reports/displacing_the_surface_costs_ink_in_both_directions.md)). It does **not** help
> comparisons between different *fits* — six seeds re-flattened deterministically give a CV of
> **0.09 [0.06, 0.22]**, statistically indistinguishable from stock (F(5,5) p=0.67), so fit RNG
> dominates there and the flatten was never the binding constraint
> ([report](reports/fit_rng_dominates_the_flatten_was_never_binding.md)). Along the way the
> project's own "pipeline is deterministic to 1.4%" floor turned out to be one draw with the wrong
> mechanism attached — the scorer it blamed contributes **0.0032%**, ~950× too little — and three
> successive seed-noise figures (0.0125 → 0.0263 → 0.0536) were each retracted when the next arm
> landed inside the interval that had never been printed. Everything is registered before the data
> exists, with the decision script committed while the first arm is still rendering; the
> [template](docs/preregistration/TEMPLATE.md) encodes what each of those cost.
> **Live experiment tracking:** [wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch).

`bountyhunter` is an experiment in having AI agents perform their own end-to-end computer vision research. It automates the cycle of hypothesis generation, hyperparameter optimization, model training, and performance evaluation to uncover the "Gold Standard" configurations for reading ancient carbonized scrolls.

## 🚀 Key Features

- **Working ink detector** (`vesuvius_autoresearch.detector`): the proven 2023 Grand-Prize TimeSformer recipe, productionized and tested, with a one-command `reproduce`. (A full-resolution ResEncUNet alternative was built and *underperformed* it under our recipe — documented, not discarded.)
- **Honest metric contract** (`detector/metrics.py` + `measure` CLI): threshold-swept F1 primary; average precision + AP-prevalence-lift as imbalance-robust gates; ROC-AUC secondary. The inherited `skeleton_distance_length` "prize gate" was **removed after we proved it invalid** (location-blind; probe included).
- **SOTA open-data tooling + distillation** (`repro/sota_data/`): anonymous-S3 access to `s3://vesuvius-challenge-open-data/`, OME-Zarr extraction, and a teacher–student distillation pipeline onto the newly-open SOTA surface volumes.
- **Surface-volume renderer** (`repro/sota_data/render_cli.py`): turns the bucket's **mesh-only** segments (`original.obj` + volume, no surface volume) into detector-ready surface volumes — one command, obj or released-tifxyz geometry, teacher-free scale inference, label-free output. Historical released-volume comparisons measured Scroll 1 NCC 0.59 and PHerc1667 NCC **0.78, gate PASS**. The [October 5 review](docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-05_SURFACE_RENDERER.md) fixes crop coordinates, depth coverage, read failures, intensity scaling, and fragment publication; those real-data comparisons need rerunning for rendering contract 2. See **[docs/SURFACE_RENDERER.md](docs/SURFACE_RENDERER.md)** for the current input and output contracts.
- **Spiral-fit measurement tooling** (`repro/spiral_render/`, `scripts/check_patch_*.py`,
  `calibrate_radius_to_winding.py`): renders legible Greek from published `spiral_datasets` artifacts
  on one 4090, with the noise floors attached — region-specific seed floors, a non-blank strip
  control, and pre-registered analyses that refuse a partial sample. Built for the spiral track
  above; reusable for any patch-selection experiment on this data.
- **Autonomous Research Loop:** samples a multidimensional configuration space (architectures, loss functions, augmentations) under fixed time budgets, with per-cycle preflight gates.
- **On-the-fly Multi-tasking:** real-time 3D Structure Tensor and Ridge Map computation for rich structural supervision.
- **Calibration Baselines:** periodic re-evaluation against the fixed 2023 Grand Prize recipe to prevent research drift.

## Quick start

**Requirements:** A single NVIDIA GPU (tested on RTX 4090/H100), Python 3.10, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies and the local src package
uv sync

# 3. Download data (~5 min)
uv run python scripts/archive/download_data.py --fragment 4

# 4. Run a single training smoke test (~30 s) to verify your setup
PYTHONPATH=. uv run python scripts/training/train.py --test

# 5. Kick off the autonomous research loop
./start.sh        # wraps: uv run python run_autoresearch_loop.py
./stop.sh         # stop the loop and pause automatic watchdog restarts
```

`start.sh` and `stop.sh` control this checkout using its process lock and work
from any directory. `start.sh` clears the pause; `make shift` uses the same
launcher. The watchdog respects the pause even when the loop is already stopped.

### Detector prediction and measurement

Each detector command accepts `--config path/to/config.json` after the subcommand.
The JSON object overrides `DetectorConfig` defaults; use the same architecture,
depth and window settings used to train the checkpoint. For example:

```json
{"data_root": "/path/to/converted_fragments", "architecture": "timesformer"}
```

New checkpoints record their detector configuration and reject mismatched model
or depth-window settings before reading fragment data. Legacy checkpoints remain
loadable with a warning to verify the supplied configuration. Set `use_tta` to
`true` to average four spatial mirror views; its default is `false`.

Training now honors `weight_decay`, `max_grad_norm`, and `warmup_factor`. Their
defaults are 0.01, 1.0, and 1.0 respectively, matching the previously executed
recipe. Earlier configuration fields advertised different values but were
ignored; explicit overrides now affect training. See the
[detector workflow guide](docs/DETECTOR_WORKFLOW.md) for these contracts.

Predict a converted fragment with layers and a fragment mask; ink labels are optional:

```bash
uv run python -m vesuvius_autoresearch.detector.cli infer \
  --config detector_config.json --checkpoint models/detector/detector_epoch=7.ckpt \
  --fragment PHercParis2Fr143 --output predictions/PHercParis2Fr143.npy
```

The float32 NumPy map has the original layer dimensions. Prediction keeps the
existing full-window mask rule: pixels not covered by a usable window are zero;
a fragment with no usable windows is an error. `eval`, `measure`, and training
still require ink labels. `measure` writes its partial report and exits nonzero
if any target fails, printing the target and error to stderr. An empty evaluation
mask or a target without both ink and background is a failed measurement.

### Prediction from an autoresearch checkpoint

The research loop's `best_model.pt` uses a different model and data contract from
the fragment detector's Lightning checkpoints. Use the CT-volume entry point for
that checkpoint:

```bash
uv run python -m scripts.production_predict \
  --checkpoint best_model.pt --uri /path/to/ct.zarr \
  --x 0 --y 0 --z 0 --width 1024 --height 1024 \
  --batch-size 16 --out-dir predictions/production
```

Patch size, depth, and ridge inputs come from the checkpoint. Stride defaults to
half the patch size; a supplied stride must be positive and no larger than the
patch. The requested region must fit inside the source volume and be at least
one patch wide and tall. The output includes a uint8 OME-Zarr group and metadata.
CLI positions are source voxel indices in x/y/z order; OME transforms use z/y/x
order in micrometers. Voxel size comes from the checkpoint when recorded, with
`--voxel-size-um` providing the fallback (default 7.91).

For regional ink/fiber overlays and ensembles, see
[CT-volume inference](docs/VOLUME_INFERENCE.md). These commands use QC gating and
optional mirror averaging; their metadata records the applied recipe. Ensemble
members must share spatial context and calibration. Partial inference shards
are identified explicitly and cannot pass complete-region submission validation.

For checkpoint re-evaluation, masked patch AUC, pseudo-labels, and manual-review
queues, see [Checkpoint analysis and labeling](docs/CHECKPOINT_ANALYSIS.md).
These tools use recorded model settings and complete weights; failed reads or
measurements produce an error instead of a successful result.

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

This suite uses a local Zarr fixture by default. To also exercise the public S3
volume (requires network access), run
`VESUVIUS_TEST_S3=1 uv run python -m pytest -q tests/test_zarr_loading.py`.
Remote open/read operations have 30-second timeouts and failures fail the test.

For submission mechanics, generate candidate commands without executing inference:

```bash
uv run python scripts/build_scroll23_search_queue.py
uv run python scripts/rank_scroll23_candidates.py
uv run python -m scripts.inference.run_ranked_inference
```

Validate an actual prediction image and supplied training/prediction masks in a
common coordinate frame. Missing masks, unreadable images, placeholder evidence,
or inconsistent export metadata fail validation. The evidence chain preserves
the original prediction metadata and writes a separate evidence record.
See [Submission evidence](docs/SUBMISSION_EVIDENCE.md) for the commands and limits.

Ranked CT crops and structure tensors can be prepared with
`scripts/execute_lasagna_pipeline.py`. It preserves candidate identity, checks
completed outputs before reuse, and reports failed candidates with a nonzero
exit. Surface fitting requires its own upstream configuration; optional CT
evidence requires supplied masks. See [Candidate preprocessing](docs/CANDIDATE_PREPROCESSING.md)
for the supported stages and the stored-tensor anisotropy measurement.

`uv run python scripts/generate_submission_package.py` creates an illustrative
dry-run package, reports `FAIL`, and exits with status 1. Supplying a real image
or scroll name does not turn its synthetic masks into verified overlap evidence.

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

The detection CLI supports CPU execution and automatic CUDA availability checks.
For semantic-model inference and connectivity scoring, see
[fiber tracing](docs/FIBER_TRACING.md). The October 4 review corrected ERL's
dependence on skeleton edge ordering and added model/image provenance to caches
and reports. Published legacy fiber rankings require recomputation with scoring
version 4, ScrollGT's definition (vendored, held by a sync test); the [review report](docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-04_FIBERS.md)
describes the change and its validation limits.

## Scroll-specific augmentations

`scroll_augmentations.py` is a standalone, dependency-light library of nine
GPU-native augmentations that model scroll-CT artifacts (beam scatter,
compression, missing slices, Rician noise, …) for ink-detection training —
addressing [villa issue #201](https://github.com/ScrollPrize/villa/issues/201).
The training loop uses it directly. See **[docs/SCROLL_AUGMENTATIONS.md](docs/SCROLL_AUGMENTATIONS.md)**
for the per-family reference, usage, and the [before/after demo](reports/augmentation_demos/all_families.png).

## License

MIT
