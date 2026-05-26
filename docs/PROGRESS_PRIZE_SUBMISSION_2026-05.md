# Progress Prize Submission (May 2026 — Part 2 of 2): Villa-Native Submission Lanes for LeJEPA / Mutex / Neural-Tracing / GP-Winner Recipes
**Submission Date:** 2026-05-15 (target: 2026-05-31 11:59pm PT)
**Submission Form:** https://forms.gle/LrpQmSAqdwGpTczLA
**Target Prize Tier:** Denarius / Sestertius (open to maintainer judgment)
**Submitter:** Jon Marrs &lt;jdmarrs@gmail.com&gt;
**Repository:** https://github.com/jonmarrs/vesuvius-autoresearch
**License:** MIT (autoresearch); upstream villa PR licensed per ScrollPrize/villa contribution terms
**Status:** FILED through the May form on 2026-05-15.
**Companion submission:** [PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md](PROGRESS_PRIZE_SUBMISSION_2026-05_part1.md) — **Part 1 of 2**, the Vesuvius-C Python bindings + autoresearch loop (work originally drafted for April 2026 but never filed; queued for filing as a second May submission since the May Progress Prize allows multiple submissions per cycle).

## Thesis

Villa already contains every ingredient needed for prize-track submissions across First Letters, First Title, and Grand Prize lanes — but the gap between "a villa trainer exists" and "an open-source tool a community member can actually run" was wide. This submission closes that gap for four villa lanes that were previously inaccessible without writing per-lane glue code, and contributes one upstream PR that makes the LeJEPA-fine-tune lane work in villa's own inference container.

## What this submission ships

### 1. A villa-baseline launcher family

Four launchers under `scripts/launch_*.py`, each following the same dry-run-by-default pattern, auto-resolving local data + checkpoints, writing a YAML config + marker JSON, and surfacing the exact subprocess command to run:

| Launcher | Villa target | Patch | Submittable | Marker |
| --- | --- | --- | --- | --- |
| `scripts/launch_gp_winner.py` | `TrainerTimesFormer` (GP-2023 recipe: TimeSformerInk + 0.5·Dice + 0.5·SoftBCE(0.25), AdamW 3e-5) | (16, 256, 256) | No (research baseline) | `reports/gp_winner_baseline.json` |
| `scripts/launch_mutex.py` | `MutexAffinityTrainer` (papyrus sheet instance segmentation; Grand-Prize-aligned) | (64, 64, 64) | Yes (≤64) | `reports/mutex_affinity_run.json` |
| `scripts/launch_neural_tracing.py` | `trace_service.py` socket daemon (VC3D / Crackle Viewer review-time tracing) | n/a (service) | n/a | `reports/neural_tracing_service.json` |
| `scripts/launch_finetune_lejepa.py` | `TrainFineTuneLEJEPA` (LeJEPA pretrain → supervised UNet) | (32, 64, 64) | Yes (≤64) | `reports/finetune_lejepa_run.json` |

Each marker is surfaced in `reports/villa_prize_action_matrix.md`'s **Villa Baselines & Lanes** section, so action-matrix readers see status, purpose, marker path, and launcher path at a glance.

A back-compat shim at `train_mutex.py` preserves the prior CLI contract from `scripts/prepare_mutex_training.py`.

### 2. An architecture-aware submission_package path

`scripts/export_for_production.py` now auto-detects model architecture from the state-dict key prefix (`backbone.` → timesformer, `encoder.` → resnet3d, `shared_encoder.` → primus_lejepa) and stamps the LeJEPA pretrain SHA + fine-tune config SHA into the envelope for `primus_lejepa`.

`scripts/smoke_test_villa_optimized_inference.py` was extended with a new `build_primus_submission_package(...)` that emits a self-contained submission folder for a Primus fine-tune (since villa's optimized_inference Docker container can't run Primus yet — see the upstream PR below):

```
submission_package_primus_lejepa/
├── model.pt
├── predict_manifest.json     # villa-native vesuvius.models.run.inference command
├── README.md                 # why this package and not Docker
├── REPRODUCIBILITY.md        # pretrain SHA, finetune config SHA, exact rerun steps
└── submission_manifest.json
```

The smoke test refuses unsupported `MODEL_TYPE`s with a clear error pointing at the package path, and the `validate_exported_checkpoint` step now sanity-checks the state-dict prefix against the declared architecture (catches the "load_state_dict silently no-ops" failure mode that the original smoke test missed).

### 3. Upstream villa PR — `model_primus.py` loader

Pull request: **https://github.com/ScrollPrize/villa/pull/899**

Adds `MODEL_TYPE=primus` to `villa/ink-detection/optimized_inference`:
- New `model_primus.py` mirrors `model_timesformer.py` / `model_resnet3d.py`, reconstructs the model via villa's own `NetworkFromConfig`, strips DDP / `_orig_mod.` prefixes, wraps in a `PrimusWrapper` implementing the `InferenceModel` protocol.
- `runtime_contracts.py` registers `"primus"` in `SUPPORTED_MODEL_TYPES`.
- `entrypoint.py` adds the dispatch branch.
- `Dockerfile` ships the new file.
- `tests/test_runtime_contracts.py` asserts the new model type is accepted.

This is the missing piece for an end-to-end **villa-only** pipeline: `villa lejepa → villa finetune_lejepa → villa optimized_inference`. Once merged, our `submission_package_primus_lejepa/` path becomes optional rather than required.

### 4. Evidence-chain integration

`scripts/run_villa_prize_evidence_chain.py` gained a `--neural-tracing` flag. When set, each per-candidate evidence directory gains a `neural_tracing.json` readiness marker showing whether `trace_service` can be launched for that candidate's volume — bringing villa's review tooling into the autoresearch prize-evidence flow.

## Why this is prize-worthy

Per the Progress Prize criteria (released early, actually used, well documented):

- **Released early.** All four launchers + the submission_package path + the upstream PR shipped during the May 2026 monthly window, well before the 2026-05-31 deadline.
- **Actually used.** The launcher family is wired into `reports/villa_prize_action_matrix.md` and `scripts/run_post_sprint_villa_handoff.py`, so each Day-Shift / Night-Shift autoresearch cycle now exercises these lanes. The original upstream villa PR #899 is no longer acceptance evidence: it was closed without merge on 2026-05-26. Treat the PR as a lesson learned and use a fresh, human-evaluated replacement PR only after the Docker smoke passes end to end.
- **Well documented.** Each launcher carries a docstring explaining its villa target, the submittability constraint, and the dry-run/execute pattern. The action-matrix Baselines section gives a one-glance status table. `REPRODUCIBILITY.md` in each emitted submission_package records the exact pretrain checkpoint SHA and fine-tune config SHA. The submission packaging story has eight passing unit tests covering prefix-mismatch detection, Docker refusal, and full package emission.

## How to reproduce

Cold clone → working launchers:

```bash
git clone --recursive https://github.com/jonmarrs/vesuvius-autoresearch.git
cd vesuvius-autoresearch
uv sync

# Dry-run every villa-baseline lane (no GPU spend, no submodule edits):
.venv/bin/python scripts/launch_gp_winner.py
.venv/bin/python scripts/launch_mutex.py
.venv/bin/python scripts/launch_neural_tracing.py --scroll-id 0125 --division div_100
.venv/bin/python scripts/launch_finetune_lejepa.py

# Refresh the action-matrix Baselines table:
.venv/bin/python scripts/build_villa_prize_action_matrix.py
cat reports/villa_prize_action_matrix.md
```

To actually train the submittable LeJEPA fine-tune (uses the existing
`checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth` and the
PHercParis2Fr47 labeled volume):

```bash
.venv/bin/python scripts/launch_finetune_lejepa.py --execute
```

To package the resulting checkpoint as a submission:

```bash
.venv/bin/python scripts/smoke_test_villa_optimized_inference.py \
  --input checkpoints/finetune_lejepa/<run>/best.pt \
  --output production_primus_lejepa.pt \
  --submission-package-dir submission_package_primus_lejepa
```

The smoke test validates the envelope, refuses the Docker command (no merged
upstream Primus optimized-inference loader yet; PR #899 was closed), and writes the `submission_package_primus_lejepa/`
directory.

## Integration with villa (component coverage)

This submission adds direct integrations beyond what the April submission covered:

1. **[`vesuvius.models.training.trainers.mutex_affinity_trainer`](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/models/training/trainers/mutex_affinity_trainer.py)** — invoked via official CLI from `scripts/launch_mutex.py`.
2. **[`vesuvius.models.training.trainers.self_supervised.train_finetune_lejepa`](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/models/training/trainers/self_supervised/train_finetune_lejepa.py)** — invoked via thin runner from `scripts/launch_finetune_lejepa.py` (the official CLI does not yet dispatch this trainer; the runner pattern bypasses cleanly without modifying the submodule).
3. **[`segmentation/models/multi-task-3d-unet/training/trainers/train_gp_winner.py`](https://github.com/ScrollPrize/villa/blob/main/segmentation/models/multi-task-3d-unet/training/trainers/train_gp_winner.py)** — invoked via runner from `scripts/launch_gp_winner.py`.
4. **[`vesuvius.neural_tracing.trace_service`](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/neural_tracing/trace_service.py)** — surfaced as a per-candidate review daemon by `scripts/launch_neural_tracing.py`.
5. **[`vesuvius.models.run.inference`](https://github.com/ScrollPrize/villa/blob/main/vesuvius/src/vesuvius/models/run/inference.py)** — referenced by every `submission_package_primus_lejepa/predict_manifest.json` as the canonical command for Primus inference. A fresh optimized-inference replacement PR is still needed because PR #899 was closed without merge.

## Community value

Before this submission, every prize-track contributor wanting to use villa's self-supervised + fine-tune family had to:

- Write a custom invocation for each trainer (LeJEPA pretrain, LeJEPA fine-tune, mutex affinity, GP-winner, neural-tracing).
- Hand-build a YAML config matching each trainer's expected fields.
- Hand-write a submission package because villa's optimized_inference container doesn't support Primus.
- Edit the villa submodule to add a Primus loader (or fork it).

This submission collapses those four steps into:
- `python scripts/launch_<lane>.py` (dry-run, default).
- `python scripts/launch_<lane>.py --execute` (real training).
- `python scripts/smoke_test_villa_optimized_inference.py ...` (package).
- Fresh replacement PR for the Primus optimized-inference loader, but only after container deps and Docker smoke evidence are complete.

The pattern is also intentionally extensible: any future villa trainer can get its own launcher by following the existing template (`launch_lejepa.py` is the smallest example at ~100 lines).

## Repository pointers (for the Google Form)

| Field | Value |
| --- | --- |
| Repository | https://github.com/jonmarrs/vesuvius-autoresearch |
| Branch | `main` |
| Key directories | `scripts/launch_*.py`, `reports/villa_prize_action_matrix.md`, `docs/VILLA_PRIZE_READINESS.md` |
| Upstream PR | PR #899 was closed without merge; replacement PR required after Docker smoke evidence |
| Tests | `tests/test_villa_baselines_launchers.py`, `tests/test_villa_optimized_inference_smoke.py` (8 passing + 80 broader autoresearch tests) |
| Reproduction entrypoint | `python scripts/build_villa_prize_action_matrix.py` then read `reports/villa_prize_action_matrix.md` |
| License | MIT |
| Continues | [PROGRESS_PRIZE_SUBMISSION.md](PROGRESS_PRIZE_SUBMISSION.md) (April 2026) |

## Public release blurb (for socials / forum announcement)

> Four new villa-native launchers landed in vesuvius-autoresearch this month:
> dry-run-by-default wrappers for villa's **LeJEPA→UNet fine-tune**, **mutex
> sheet instance segmentation**, **neural_tracing trace_service**, and the
> **GP-2023 TimeSformer recipe** as a fixed baseline. Plus an
> architecture-aware `submission_package` path that turns a Primus
> fine-tuned `.pth` into a reviewable Progress Prize submission today
> (using villa's own `models/run/inference.py`), and an upstream PR to
> villa adding the missing `model_primus.py` loader to
> `optimized_inference` (ScrollPrize/villa#899). The action matrix at
> `reports/villa_prize_action_matrix.md` shows status for all four lanes
> at a glance.
