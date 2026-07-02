# Reproduce

Environment used for the runs below: single NVIDIA RTX 4090, Python 3.10/3.11,
dependencies pinned via `uv`.

## 1. Environment

```bash
uv sync
```

## 2. Preflight (build the model + one forward/backward)

This is the fastest end-to-end check that the codebase and model are runnable. It
builds the configured architecture and runs one forward/backward pass on a
synthetic batch — no data download required.

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

## 4. Detector unit tests (CPU)

The productionized detector and the SOTA tooling ship their own suites:

```bash
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py -q   # 29 passed (2026-07-01)
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_*.py -q      # 17 passed (2026-07-02)
```

## 5. Reproduce the working detector (GPU, ~hours)

Trains the proven TimeSformer recipe on `PHercParis2Fr47`, evaluates held-out
`PHercParis2Fr143`, and asserts the result:

```bash
uv run python -m vesuvius_autoresearch.detector.cli reproduce
```

Reproduced 2026-06-29 (best epoch by held-out selection: ROC-AUC 0.709; under the
community contract `val_f1` 0.393 / prevalence-lift 2.07 — see
`reports/detector/REPRODUCTION.md`). Cross-fragment measurement of any checkpoint:

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
column -t -s$'\t' results.tsv | less
```

The loop's `val_bpb` history is retained for provenance; note that `val_bpb` was
demonstrated to be a weak discriminator (see `FINDINGS.md`) — the honest numbers are
the detector reports above.

## 8. Run the loop (optional, long-running)

```bash
uv run run_autoresearch_loop.py
```

Each cycle samples a configuration, preflights it, trains under a fixed budget,
evaluates on the held-out fragment, and appends a row to `results.tsv`.

## Related: GPU fiber/ridge tooling

The production-scale GPU fiber/ridge detection contributed upstream is validated
separately (parity vs NumPy 1.7e-10; tiled 512³ within ~1.0 GB GPU memory). See the
fibers PR / `reports/fibers_gpu_validation_2026-06.md`.
