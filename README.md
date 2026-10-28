# bountyhunter: Vesuvius Autoresearch

*Single-GPU experiments and software contributions for the Vesuvius Challenge.*

Start with the [current research plan](docs/research_plan.md) for work that fits
one RTX 4090 (24 GB), the [research strategy](docs/RESEARCH_STRATEGY.md) for
evidence and stop criteria, and the [October filing plan](docs/PRIZE_PLAN_2026-10_FINAL_WEEK.md)
for completed contributions. The priorities are useful upstream engineering,
fiber-tracing improvements and controlled evaluation. New research claims need
measurements; internal tooling and merged PR counts alone do not establish impact.

**Check a checkout without starting training:** `python3 scripts/workspace_status.py`.
This reads setup and process metadata; it does not load model weights, read study
measurements or access CUDA. Use `--json` for a structured report. A passing setup
check is not a GPU, model-compatibility or prize-eligibility check.
See [status output and next steps](docs/WORKSPACE_STATUS.md).

**Window limits:** the project's existing 64-pixel recipe and artifact checks are
local evaluation contracts. Current official reading-prize rules allow larger
windows with evidence against hallucination. See the [rules and limitations](docs/RESEARCH_STRATEGY.md);
the legacy `submittable` flag does not establish official eligibility.

The following results summarize the earlier ink and spiral research; current
priorities and pending experiments are in the plan above.

> **Honest results, methodology, and negative results:** see [FINDINGS.md](FINDINGS.md). Current headlines: a **working, window-compliant ink detector** (held-out same-scroll `val_f1` 0.393 / prevalence-lift 2.07, its epoch chosen on that fragment, [reproduction](reports/detector/REPRODUCTION.md)), the **first valid cross-scroll measurement** (lift 1.29 — the quantified generalization gap), a **SOTA-distilled model** (`val_f1` 0.662 / lift 3.24 *agreement-with-teacher* on the open SOTA data, the best of 12 epochs on the held-out region, [report](reports/detector/sota_distill_measurement.md)), **measured cross-scroll distillation**: training-scroll diversity lifts unseen-scroll transfer 1.22 → 2.12 at fixed budget (2.12 is the best epoch on that region, so optimistic by an unmeasured amount), and a third scroll shows no measured gain over that selected row (≈2.1, the third-scroll model's last epoch; a gain over a fixed-rule row is not excluded) ([diversity](reports/detector/cross_scroll_distill.md), [scaling](reports/detector/cross_scroll_scale.md)); and — the load-bearing result — a **ground-truth calibration** built by registering 2023 hand labels onto the SOTA flattening: against human labels the canon prediction scores ROC-AUC 0.70–0.75 (0.70 on a segment since retired non-scoring; corrected 2026-10-16, this said 0.56–0.70, 0.56 being the retracted held-out figure), and on a **held-out** segment the clean distilled students read **ROC-AUC 0.731–0.746 / lift 2.3–2.4** against a constant-prediction ROC-AUC floor of 0.500 (the near-constant legacy detector scored 0.518) ([report](reports/detector/registered_gt_heldout_validation.md)) — genuine held-out generalization, at or just under the canon teacher's 0.753 there on ROC-AUC, which understates the binary teacher (on F1 at 0.5 the teacher leads, 0.572 vs 0.44–0.45), so read it as faithful distillation of a teacher that *does* read rather than as beating it. **Corrected 2026-08-07:** this previously said the students read near chance; that was a hardcoded-constant bug in our own registration, found and published as a retraction ([detail](reports/detector/registration_offset_2026-08-07.md)). July: the surface renderer **gate-PASSED a second-scroll validation** (PHerc 1667 clean triple, NCC 0.78 vs pre-registered 0.60; Scroll 1's 0.59 confirmed as a resolution-mismatched comparison), rendered independent surface volumes of PHerc 1667's merged full-reading geometry (note: villa's own `vc_obj2tifxyz` + `vc_render_tifxyz` already cover both of our input paths more capably — an earlier "for the first time" framing here was wrong), and the published reading's 22 columns were registered onto that geometry as **[ScrollGT](https://github.com/jonmarrs/scrollgt)'s first non-training-scroll target** — on which our own models measure at the floor (arm C col-vs-gutter AUC 0.575 against a noise floor of 0.578 on the definitive full-band n=18v17 rows, i.e. statistically at the floor, texture not letterforms; an earlier 0.667 here came from a superseded n=3v2 extreme; [report](reports/detector/scrollgt_v02_columns.md)). Earlier over-reads (the "64 px window is learnability-limited" claim; a first over-optimistic ground-truth framing) were caught and corrected — see FINDINGS.
> **September 2026 research — spiral fitting.** villa deprecated `ink-detection/` in late August, so
> active work moved to `spiral-fitting/`. Headline: villa's loop optimises recovered ink
> (`total_fg_pixels`) with a geometry cross-check (`satisfied_area`), and we have **four
> pre-registered cases where those move independently** — a config change that improved geometry
> +1.03% (5 fits against 6) while costing **-10.35% of the ink** (6 against 6), two refits that
> raised geometry **+17.66% and +16.24% for no ink gain at all**, and an ablation of **5,413 winding
> constraints** that measurably *degraded* the geometry (-0.69%, p=0.0027) while reading held. The
> fourth bears on strategy:
> winding constraints are what villa names as the fastest path to unrolling at scale. The second answers an avenue villa names in its open
> problems ("automatically crop 'good' regions of the spiral fit... as surface patch inputs to a
> subsequent run") with a **registered FAILURE — twice**, the second study built to rule out the
> obvious confound in the first and designed while the first's results were still unread. Both
> geometry gains are **circular by construction** — the arm is selected on satisfaction and then
> scored on it — which is exactly why a loop using that guard would read either as success; and both
> ink nulls are bounded at ~12%, not zero (~10% as registered; corrected 2026-09-12 with the
> pinned tier's noise floor). *(Corrected 2026-10-23: ~12% is the design MDE. The data rule out only
> effects outside [−18.4%, +16.7%] and [−20.7%, +13.1%].)* **All of it measured on villa-spiral `6847063f`;
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
> deterministic algorithms makes it **bit-reproducible** (identical `x/y/z.tif` by md5) at 9.5×
> lower flatten throughput, ~11 min against ~4 per flatten and 2 h renders
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
> mechanism attached — the scorer it blamed contributes **0.0032%**, ~440× too little — and the
> seed-noise figure was published too low twice: 0.0125, withdrawn when a third arm moved it to
> 0.0263, and 0.0263, withdrawn when six fits already on disk doubled it to 0.0536. Both times the
> new value sat inside the published interval: the point estimate was wrong, not the interval.
> Everything is registered before the data
> exists, with the decision script committed while the first arm is still rendering; the
> [template](docs/preregistration/TEMPLATE.md) encodes what each of those cost.
> **Live experiment tracking:** [wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch).

`bountyhunter` is an experiment in having AI agents perform their own end-to-end computer vision research. It automates the cycle of hypothesis generation, hyperparameter optimization, model training, and performance evaluation to uncover the "Gold Standard" configurations for reading ancient carbonized scrolls.

## 🚀 Key Features

**September 2026 Progress Prize:** Jonathan Marrs was awarded $250 for “assorted
useful merged villa PRs,” as credited in the supplied Discord announcement.
See [award history and source](docs/PROGRESS_PRIZE_AWARDS.md).

- **Working ink detector** (`vesuvius_autoresearch.detector`): the proven 2023 Grand-Prize TimeSformer recipe, productionized and tested, with a one-command `reproduce`. (A full-resolution ResEncUNet alternative was built and *underperformed* it under our recipe — documented, not discarded.)
- **Honest metric contract** (`detector/metrics.py` + `measure` CLI): threshold-swept F1 primary; average precision + AP-prevalence-lift as imbalance-robust gates; ROC-AUC secondary. The inherited `skeleton_distance_length` "prize gate" was **removed after we proved it invalid** (location-blind; probe included).
- **SOTA open-data tooling + distillation** (`repro/sota_data/`): anonymous-S3 access to `s3://vesuvius-challenge-open-data/`, OME-Zarr extraction, and a teacher–student distillation pipeline onto the newly-open SOTA surface volumes.
- **Surface-volume renderer** (`repro/sota_data/render_cli.py`): turns the bucket's **mesh-only** segments (`original.obj` + volume, no surface volume) into detector-ready surface volumes — one command, obj or released-tifxyz geometry, teacher-free scale inference, label-free output. Historical released-volume comparisons measured Scroll 1 NCC 0.59 and PHerc1667 NCC **0.78, gate PASS**. The [October 5 review](docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-05_SURFACE_RENDERER.md) fixes crop coordinates, depth coverage, read failures, intensity scaling, and fragment publication; those real-data comparisons need rerunning for rendering contract 2. See **[docs/SURFACE_RENDERER.md](docs/SURFACE_RENDERER.md)** for the current input and output contracts.
- **Spiral-fit measurement tooling** (`repro/spiral_render/`, `scripts/check_patch_*.py`,
  `calibrate_radius_to_winding.py`): renders legible Greek from published `spiral_datasets` artifacts
  on one 4090, with the noise floors attached — region-specific seed floors, a non-blank strip
  control, and pre-registered analyses that refuse a partial sample. Built for the spiral track
  above; reusable for any patch-selection experiment on this data.
- **Autonomous Research Loop:** each cycle applies one tweak to the promoted configuration (learning rate,
  weight decay, batch size, loss weights, ridge sigma, augmentation backend, fiber target, multi-task heads,
  UA-MT settings) and trains it for a fixed time, after a preflight. Architecture and model size are
  pinned to the production `resenc_unet`, so every cycle warm-starts from `best_model.pt`.
- **On-the-fly Multi-tasking:** real-time 3D Structure Tensor and Ridge Map computation for rich structural supervision.
- **Noise calibration:** the [repeatability probe](docs/REPEATABILITY_PROBE.md)
  (`scripts/f1_noise_probe.py --config … --checkpoint … --out … --execute`) measures the run-to-run F1 spread on
  demand. It is run by hand and does not set the promotion tolerance. (The loop's periodic 2023 Grand-Prize-recipe
  baseline was removed on 2026-10-12: its VRAM estimate skipped it every time.)

## Quick start

**Requirements:** A single NVIDIA GPU (tested on RTX 4090/H100), Python 3.10, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies and the local src package, and check out the pinned
#    ScrollPrize/villa (the loop's topology metrics and villa augmentations)
uv sync
git submodule update --init villa

# 3. Check the code (no data or GPU needed; it writes only caches)
make smoke

# 4. With the data in place (below), check the loop's configuration: builds the
#    model and runs one forward/backward on the CPU (writes nothing)
PYTHONPATH=. uv run python scripts/training/train.py --smoke

# 5. Score best_model.pt under the current validation protocol (best on the GPU;
#    reads the validation fragment; rewrites best_model.pt's stored scores)
uv run python scripts/reevaluate_best_model.py --update-stored

# 6. Kick off the autonomous research loop
./start.sh        # runs run_autoresearch_loop.py in the background; output in autoresearch.out
./stop.sh         # stop the loop and pause automatic watchdog restarts
```

On a host where the `vesuvius` package was installed from `villa/vesuvius` (it is
outside `uv.lock`), do not run `uv sync` (or `make install`, which runs it) again
in that checkout: an exact sync removes it
([resume note](docs/RESUME_AFTER_RESTART.md), 2026-10-13). `config.json` has
`use_wandb: true`, so runs log to wandb online (`wandb login`), falling back to
offline if that fails; `WANDB_MODE=offline` keeps them local.

**Data.** `config.json` trains on `local_data/PHercParis2Fr47/surface_volume.zarr`
and validates on `local_data/PHercParis2Fr143/surface_volume.zarr`. Each needs
its ink labels beside it (`inklabels_refined.png`, `inklabels_filled.png` or
`inklabels.png`, the first found). A `mask.png` there, if present, limits where
patches are drawn, and a `patches.json` replaces the patch catalogue. A
`<segment>_pseudo.png` in `pseudo_label_dir` (`local_data/pseudo_labels`)
replaces a training volume's labels, and is refused while `use_confidence_weight`
is off ([pseudo-label handoff](docs/PSEUDO_LABEL_HANDOFF.md)). No maintained command in this
repository builds these directories. The downloaders in `scripts/archive/` are
unmaintained and fetch raw CT, TIFF layers or label PNGs, not these zarrs; the
`download_data.py --fragment 4` this guide used to give names a moved script,
downloads nothing and exits 0.

**Score the incumbent before the first start.** The loop compares each cycle
with the val_f1 stored in `best_model.pt`, and starts only if that score was
measured under the current validation protocol (`scripts/training/promotion.py`,
including `config.json`'s `depth_band`). Otherwise it prints `Not starting: …`
with the command to run, and returns. Step 5 does that; repeat it after any
protocol change, and after any change to the validation inputs (label file,
mask, `patches.json`). It rewrites the tracked `best_model.pt`; commit it, as
`a37b05c4` did. `start.sh` reports that it launched the loop, not that a cycle
began: the loop's own output, including any refusal, is in `autoresearch.out`.

Avoid `train.py --test`. It is not a setup check: it is a training run with a
30 s budget followed by the full validation, it needs CUDA and takes no lock,
and it writes the loop's state: `history.tsv`, `last_model.pt` and
`run_result.json`, and, if it beats the incumbent, `best_model.pt`, `results.tsv`
and `prize_readiness.tsv`. Such a promotion leaves `config.json` as it was, so it
no longer describes `best_model.pt`.

`start.sh` and `stop.sh` control this checkout using its process lock and work
from any directory. `start.sh` clears the pause, even when it then refuses
because other work holds the lock; `make shift` uses the same launcher. The loop
ends each shift and exits (day 07:00–19:00, night 19:00–07:00, system local
time). The watchdog, `scripts/loop_watchdog.sh`, starts it again: install it
with `crontab -e`, adding `*/5 * * * * /path/to/checkout/scripts/loop_watchdog.sh`
and `@reboot /path/to/checkout/scripts/loop_watchdog.sh`. It logs to
`watchdog.log`. Cron's `PATH` has no `uv`: the watchdog adds `~/.local/bin`, so
if `uv` is elsewhere set `PATH=` in the crontab (otherwise the launch fails, and
says so only in `autoresearch.out`). It respects the pause even when the loop is already stopped, so
after `stop.sh` nothing restarts the loop until `start.sh` runs; without the
watchdog, `start.sh` gives at most one shift.
The lock is also held by the work that must not run beside the loop: the noise
probe (`scripts/f1_noise_probe.py --execute`), the augmentation ablation
(`scripts/ablate_scroll_augmentations.py`, unless `--dry-run`) and the incumbent re-score
(`scripts/reevaluate_best_model.py --update-stored`). Each refuses to start
while another holds it, and `stop.sh` stops whichever does. It also stops the
training runs a killed loop or ablation left going (each runs in a session of its
own), and names any started by hand; `scripts/loop_control.py status` lists them.
While such a run is going, the loop, the noise probe, the ablation and the re-score refuse to
start.

### Detector prediction and measurement

Each detector command accepts `--config detector_config.json` after the subcommand
(a detector configuration, not the loop's root `config.json`).
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
[CT-volume inference](docs/VOLUME_INFERENCE.md). These commands use optional
mirror averaging; their metadata records the applied recipe. Ensemble
members must share spatial context and calibration. Partial inference shards
are identified explicitly and cannot pass complete-region submission validation.

For generic weighted tensor means and the status of the legacy First Title
launcher, see [Ensemble voting](docs/ENSEMBLE_VOTING.md). Voting checks numerical
compatibility; it does not establish accuracy or eliminate hallucinations.

For checkpoint re-evaluation, masked patch AUC, pseudo-labels, and manual-review
queues, see [Checkpoint analysis and labeling](docs/CHECKPOINT_ANALYSIS.md).
These tools use recorded model settings and complete weights; failed reads or
measurements produce an error instead of a successful result.
Strict reads also require requested preprocessing to succeed: an unavailable
flattening backend or fabricated ridge features cannot support a validation score.

For preparing a pseudo-label batch from an explicit teacher and region manifest,
see [Pseudo-label handoff](docs/PSEUDO_LABEL_HANDOFF.md). Dry run is the default;
execution preserves known manual labels and publishes filenames the trainer
consumes. Preparation records no retraining or accuracy claim.

For exact spatial mask partitions and real dataset scan/visualization commands,
see [Spatial partitions and inspection](docs/SPATIAL_PARTITIONS_AND_INSPECTION.md).
These publish new artifacts and inspect actual masked samples; disjoint mask
pixels alone do not certify independent CT patch contexts.

For a bounded local-file inventory and a binary ink-label overview, see
[Local data catalogues](docs/DATA_CATALOGUES.md). These publish new report bundles,
record inspection limits and source fingerprints, and report mask shape checks
without inferring dataset readiness or physical registration.

For relative angle estimates from an explicit JSON graph, see
[Sheet-graph diagnostics](docs/SHEET_GRAPH_DIAGNOSTICS.md). These report
reachability, chosen paths, and constraint residuals; physical sheet stitching
and the legacy Thaumato solver sweep remain unsupported.

For descriptive comparisons of existing candidate ink maps and binary fiber
labels, see [Candidate ink/fiber reports](docs/CANDIDATE_INK_FIBER_REPORTS.md).
These reports check array and recorded prediction geometry, preserve failed
candidate records, and state the limits of shape-only alignment.

For the registered fiber-mask shift and threshold checks, see
[Fiber mask miss diagnostic](docs/FIBER_MISS_DIAGNOSTIC.md). A full verdict
requires the 21-target sample; named subsets are descriptive. Results use
explicit input paths and publish a new JSON artifact.

For CT-gated 3D ink pseudo-labels and upstream segmentation curation, see
[Volumetric label workflows](docs/VOLUMETRIC_LABELS.md). These separate heuristic
workflows declare alignment and evaluated coverage, preserve source IDs during
curation, and publish new completed artifacts. Their outputs need independent
validation before use as training ground truth.

For preparing curated sheet-instance labels for Mutex, see
[Mutex data handoff](docs/MUTEX_DATA.md). It requires explicit CT pairing,
preserves IDs and masked coverage, and checks the pinned dataset on CPU before
training. The current pinned runtime has import and channel-shape blockers;
preparation success does not establish a working training run.

For manual volume registration, probability-grid OBJ previews, and explicit
stored/full Tifxyz coordinate tiles, see [Geometry handoffs](docs/GEOMETRY_HANDOFF.md).
These workflows validate coordinate and publication contracts; alignment accuracy
and submission eligibility require separate evidence.

For validated stored-grid Tifxyz subsampling and the status of the legacy
automatic flattening selector, see [Mesh preparation](docs/MESH_PREPARATION.md).
Sampling preserves valid retained coordinates and masks; rendered alignment
and reading quality need independent checks.

For the local Python Zarr read contract and comparable timings on an explicit
voxel region, see [Local volume reads and benchmarking](docs/LOCAL_VOLUME_READS.md).

## Running the agent

Spin up your coding agent of choice in this repo, then prompt something like:

```
Hi, have a look at docs/program.md and let's kick off a new experiment!
```

The `program.md` file is essentially a super lightweight "skill".

## 📈 Tracking progress

For descriptive experiment charts and PDFs with captured source provenance,
see [Recorded experiment reports](docs/EXPERIMENT_REPORTS.md). These reports show
auxiliary diagnostics and recent rows; the frozen TSV omits the F1/AP-lift
promotion metrics.

- **`history.tsv`**: one row for every `train.py` run that finishes validation (loop cycles and runs by
  hand; not the noise probe's or the ablation's runs, which keep their own records): `val_bpb`, the topology
  diagnostics, mean AP, throughput, VRAM and the full config JSON. It has no val_f1, the metric that decides
  promotion; that is in `sprint_logs/` and each run's `run_result.json`.
- **`results.tsv`** (local, gitignored): one row per promotion, that is, a run whose val_f1 beat
  `best_model.pt`'s stored val_f1 by more than the noise tolerance (0.01 since 2026-10-17; 0.03 before), with an AP-prevalence lift above
  1.02, on the same validation protocol and inputs. Its frozen schema has no val_f1 column.
- **`prize_readiness.tsv`**: one row per promotion, recording the promoted model's window and topology gate
  results. They are recorded only: they do not block promotion while `enforce_prize_gates` is false. When
  the loop undoes a promotion (the cycle failed after it), it removes that row from both files.
- **`docs/LAB_NOTEBOOK.md`**: High-level strategic record of research milestones.
- **`sprint_logs/`**: one Markdown log per shift (a restart within the shift appends to it): each cycle's
  tweak, config, val_f1 and other statistics, and result.
- **`cycles.jsonl`** (local, gitignored): one JSON line per loop cycle that ran (scored, crashed or failed its
  preflight): its sprint log and cycle number, start, budget and tweak, the commit it ran and any working-tree
  change to what a cycle runs, its status, and the run's `run_result.json` (val_f1, ROC AUC, AP lift, steps),
  or null when the cycle was not scored. Analyses read it instead of matching sprint logs to `run.log`.
- **Logs** (local): `run.log` collects the cycles' training output (moved to `run.log.old` once past
  10 MB), `autoresearch.out` the loop's own output, and `watchdog.log` the watchdog's. `run.log.old` is
  tracked by git (since June), so each rotation shows as a change to it.

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

Checkpoint export validates recorded local settings and complete weights before
publishing a new envelope. Its handoff report distinguishes local weight checks
from upstream inference verification; registry Docker templates do not load the
exported checkpoint, and legacy Primus packages are archives with no verified
inference command. See [Checkpoint export](docs/CHECKPOINT_EXPORT.md) for commands,
provenance, supported contracts, and migration.

## 🔬 Evidence & upstream contributions

- **GPU fiber/ridge detection for villa** ([ScrollPrize/villa#1033](https://github.com/ScrollPrize/villa/pull/1033)): closed-form 3×3 eigensolver replacing the cuSolver path that fails past ~64³, with tiled/halo execution (512³ in ~1 GB VRAM) and tiled-vs-dense parity tests. Validation details in [`reports/fibers_gpu_validation_2026-06.md`](reports/fibers_gpu_validation_2026-06.md).
- **Real-scroll runs:** vesselness on a 256³ PHerc0332 region in ~1.2 s — [contact sheet](reports/real_scroll_evidence/vesselness_contact_sheet.png), plus Scroll 2/3 candidate evidence under [`reports/scroll23_evidence/`](reports/scroll23_evidence/).
- **Historical optimized-inference diagnostics:** [`reports/primus_optimized_inference_validation_2026-06.md`](reports/primus_optimized_inference_validation_2026-06.md). Current checkpoint-envelope checks do not verify a native Primus inference handoff; see [Checkpoint export](docs/CHECKPOINT_EXPORT.md).
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
src/vesuvius_autoresearch/core/model_wrappers.py — builds the loop's production resenc_unet
vesuvius_model.py        — alternative architectures (GatedUNet, TimeSformer, MedNeXt, LeJEPA-UNet, ...)
scroll_augmentations.py  — scroll-specific augmentations (decohesion, squeeze, z-dropout, ...)
scripts/                 — inference, labeling, evaluation, and prize-packaging tools
docs/program.md          — agent instructions
pyproject.toml           — dependencies
```

## Design choices

- **Autonomous Tweak Families.** The loop script (`run_autoresearch_loop.py`) samples one tweak per cycle from
  "families" (learning rate, loss balance, batch, UA-MT, features, ...), weighted by recent success: a family's
  weight decays by ×0.95 per scored cycle (floor 1) and gains 1 per promotion. Architecture and size are
  pinned.
- **Fixed Time Budget.** Training runs for a fixed wall-clock budget (default 15 mins for both shifts; nights ran 60 mins from 2026-04-29 to 2026-10-20, when a replicated study found no measurable gain from them). This ensures experiments are comparable and the agent optimizes for the best model *within the available compute*.
- **Multi-task Supervision.** Models are trained not just on ink labels, but also on auxiliary tasks like 3D ridge detection and structure tensor alignment to improve generalization.

The [repeatability probe](docs/REPEATABILITY_PROBE.md) defaults to a read-only
plan. Explicit execution isolates trials and reports F1 spread only for a complete,
valid set of runs; it does not calibrate the promotion tolerance automatically.

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
