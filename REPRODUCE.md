# Reproduce

Environment used for the runs below: single NVIDIA RTX 4090, Python 3.10,
dependencies pinned via `uv`. (Corrected 2026-10-17: this said 3.10/3.11; `pyproject.toml` requires
`>=3.10,<3.11`. The re-runs dated 2026-10-17 were on a CPU-only container with no scroll data.)

## 1. Environment

```bash
uv sync
git submodule update --init villa   # the pinned ScrollPrize/villa
```

The README's Quick start has the full setup, data placement included. (Added 2026-10-17, as in the
README: the loop's topology metrics and villa augmentations come from the submodule.)

## 2. Preflight (build the model + one forward/backward)

This is the fastest end-to-end check that the codebase and model are runnable. It
checks that each configured training volume has its label file, then builds the
configured architecture and runs one forward/backward pass on a synthetic batch.
So it needs the label files of `config.json`'s training volumes under `local_data/`, though not
the volumes themselves. (Corrected 2026-10-17: this said "no data download required", which
held until the label check was added on 2026-10-14. Without them it ends
`PREFLIGHT FAILED: no label file for training volume local_data/PHercParis2Fr47/surface_volume.zarr ...`,
exit 1.)

```bash
PYTHONPATH=. uv run python scripts/training/train.py --config config.json --smoke
```

Expected last line: `PREFLIGHT OK` (exit 0). Reproduced 2026-06-04.

> Note: the repo root must be on `PYTHONPATH` for the `scripts.*` imports
> (`PYTHONPATH=.`). `run_autoresearch_loop.py` sets this itself; the bare
> `scripts/training/train.py` invocation needs it explicitly.

## 3. Smoke test suite

```bash
uv run python scripts/smoke_test.py            # run all
uv run python scripts/smoke_test.py --list-only # list test names
```

**Current status (reproduced 2026-06-04): 9 passed, 2 skipped, 0 failed.**

Passing: `imports`, `build_resenc_unet`, `build_gated_unet` (forward+backward,
all heads), `multi_task_heads_dummy_default`, `multi_task_heads_real_outputs`,
`best_model_loads` (loads 274/274 compatible tensors), `dataloader_3tuple_sobel`,
`augmentations_albumentations`, `bandit_templates`.

Skipped (optional capabilities, by design — not failures):
- `dataloader_frangi_target` — the GPU Frangi target degrades to a zero-fallback
  when CuPy cannot use a CUDA device in this process; the test skips rather than
  asserting GPU availability.
- `augmentations_bg2` — requires the optional villa `create_training_transforms`
  augmentation, which is not installed in the base environment.

(Noted 2026-10-17: the result depends on the environment. `dataloader_3tuple_sobel` and
`dataloader_frangi_target` skip without the training data, and `augmentations_bg2` passes once the
villa submodule of §1 is checked out. The 2026-10-17 re-run, with villa at the pin and no data, was
also 9 passed and 2 skipped, but the two dataloader tests were the skips. With both, a host where
CuPy has no GPU should give 10 passed and 1 skipped.)

## 4. Detector unit tests (CPU)

The productionized detector and the SOTA tooling ship their own suites:

```bash
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py -q   # 206 passed, 1 skipped, ~3m (re-run 2026-10-17)
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_*.py -q      # 106 passed, ~11s (re-run 2026-10-17)
```

(Updated 2026-10-17: these read 30 and 60 passed, from 2026-09-06; both suites have grown since.
The 2026-10-17 SOTA run stood in an empty module for `s3fs`, which `uv sync` installs and that
machine lacked; three of the files import `repro.sota_data` modules that need it.)

## 5. Reproduce the working detector (GPU, ~hours)

Trains the proven TimeSformer recipe on `PHercParis2Fr47`, evaluates held-out
`PHercParis2Fr143`, and asserts the result:

```bash
uv run python -m vesuvius_autoresearch.detector.cli reproduce
```

Run it from the repository root: its first step converts `local_data/<fragment>/surface_volume/NN.tif`,
`inklabels.png` and `mask.png` into the detector's 8-bit layout under `data_root`
(`villa/ink-detection/train_scrolls` by default). A fragment is converted again whenever any file the
detector reads for it is missing. (Added 2026-10-17.)

Reproduced 2026-06-29 (best epoch by held-out selection: ROC-AUC 0.709; under the
community contract `val_f1` 0.393 / prevalence-lift 2.07 — see
`reports/detector/REPRODUCTION.md`). That epoch was chosen on the fragment it is reported on.
`reproduce` itself scores the epoch with the lowest mean training loss, prints its path, and
asserts ROC-AUC ≥ 0.70 on it, so its figure need not be 0.709. (Added 2026-10-22.)
Cross-fragment measurement of any checkpoint:

```bash
uv run python -m vesuvius_autoresearch.detector.cli measure --checkpoint <ckpt>
```

Reproduced 2026-06-30 (`reports/detector/cross_scroll_measurement.md`).

## 6. SOTA distillation (network + GPU, ~hours)

End-to-end against the open bucket (`s3://vesuvius-challenge-open-data/`, anonymous —
no credentials required). Run the subcommands in order:

```bash
uv run python -m repro.sota_data.distill_run prep      # fetch teachers + extract regions
uv run python -m repro.sota_data.distill_run baseline  # chance-floor baseline (GPU)
uv run python -m repro.sota_data.distill_run train     # ~10 h on an RTX 4090
uv run python -m repro.sota_data.distill_run measure   # best epoch + report + renders
```

Reproduced 2026-07-02: held-out agreement-with-teacher `val_f1` 0.372 → 0.662,
lift 0.98 → 3.24 (`reports/detector/sota_distill_measurement.md`). All metrics are
agreement with the released canon predictions, not ground-truth accuracy.

## 7. Inspect the loop's logged search results

```bash
column -t -s$'\t' history.tsv | less
```

`history.tsv` is tracked and has a row for every `train.py` run that finished validation, except
experiment runs with `checkpoint_out` set (the noise probe's and the ablation's). Its `val_bpb` and
topology columns are retained for provenance; `val_bpb` was demonstrated to be a weak discriminator
(see `FINDINGS.md`), and neither decides promotion now. val_f1, the metric that does, has no column
here: it is in each shift's `sprint_logs/` log, and the latest run's local `run_result.json`. The
README's "Tracking progress" section describes every log. The honest numbers are the detector
reports above.
(Corrected 2026-10-17: this pointed at `results.tsv`, which is local and gitignored, with one row
per promotion.)

## 8. Run the loop (optional, long-running)

```bash
uv run python scripts/reevaluate_best_model.py --update-stored   # score the incumbent first
./start.sh                                                       # the loop, in the background
```

Each cycle samples a configuration, preflights it, trains under a fixed budget,
evaluates on the held-out fragment, and appends a row to `history.tsv`. A cycle whose val_f1 beats
the incumbent's by more than 0.01 (0.03 before 2026-10-17), with an AP-prevalence lift above 1.02, on the same validation
protocol and inputs, is promoted to `best_model.pt` and also gets a row in `results.tsv`.

The README's Quick start (steps 5 and 6) and the paragraphs after it give the prerequisites: the
loop starts only if `best_model.pt`'s score was measured under the current validation protocol
(otherwise it prints `Not starting: …`), it exits at the end of its shift, and the watchdog, once
installed, starts it again. (Corrected 2026-10-17: this gave a bare `uv run run_autoresearch_loop.py`, and said every
cycle appends to `results.tsv`.)

## 9. Spiral fitting (the current track)

The sections above are the detector work. Since villa deprecated `ink-detection/` in late August the
active track is spiral fitting, which has its own reproduce guide because it needs a villa checkout,
a container and ~10 GB per arm:

**[repro/spiral_render/README.md](repro/spiral_render/README.md)** — renders legible Greek from
published `spiral_datasets` artifacts on one consumer GPU, and documents nine obstacles that each
cost hours to find (wrong scale writing a black strip, the scorer OOMing at outer windings, a stale
published container binary, ~1 GB of RAM headroom during a render).

```bash
./repro/spiral_render/preflight.sh    # checks every prerequisite, ~5s, names what is missing
```

Run that first; it fails in seconds rather than at band 18 of a two-hour render. The pre-registered
studies built on this path are in `reports/` — start with
[SPIRAL_FINDINGS_SUMMARY.md](reports/SPIRAL_FINDINGS_SUMMARY.md).

## Related: GPU fiber/ridge tooling

The production-scale GPU fiber/ridge detection contributed upstream is validated
separately (parity vs NumPy 1.7e-10; tiled 512³ within ~1.0 GB GPU memory). See the
fibers PR / `reports/fibers_gpu_validation_2026-06.md`.
