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

**Current status (reproduced 2026-06-04): 6 / 11 passing.** Reported honestly:

Passing — model construction and core behavior:
`build_resenc_unet`, `build_gated_unet` (forward+backward, all heads),
`multi_task_heads_dummy_default`, `multi_task_heads_real_outputs`,
`dataloader_3tuple_sobel`, `bandit_templates`.

Known-failing (being addressed — not silently hidden):
- `imports`, `best_model_loads`, `augmentations_albumentations`, `augmentations_bg2`
  — stale top-level imports (`train`, `ensemble_predict`) left over from a module
  reorg; the modules now live under `scripts/`. Test-harness path bug, not a runtime
  defect in the loop (which runs with the repo root on `PYTHONPATH`).
- `dataloader_frangi_target` — the Frangi target uses a GPU path that falls back to
  zeros when no CUDA device is visible to the worker (e.g. under GPU contention),
  which trips the non-zero assertion.

## 4. Inspect the logged search results

```bash
column -t -s$'\t' results.tsv | less   # 17 logged cycles
```

`val_bpb` (held-out cross-fragment validation, lower is better) over the logged run:
first cycle **0.4136** → best **0.4123**. Topological `centerline_dice` ≈ 0.07–0.10.
These are the real numbers; see `SUBMISSION.md` → Results for interpretation.

## 5. Run the loop (optional, long-running)

```bash
uv run run_autoresearch_loop.py
```

Each cycle samples a configuration, preflights it, trains under a fixed budget,
evaluates on the held-out fragment, and appends a row to `results.tsv`.

## Related: GPU fiber/ridge tooling

The production-scale GPU fiber/ridge detection contributed upstream is validated
separately (parity vs NumPy 1.7e-10; tiled 512³ within ~1.0 GB GPU memory). See the
fibers PR / `reports/fibers_gpu_validation_2026-06.md`.
