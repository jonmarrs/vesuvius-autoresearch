# Design and architecture review — the owner's 2026-10-14 training-data changes

Date: 2026-10-16. Baseline: `b1541e51` (main after #91). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: five commits the owner made to main on 2026-10-14, which no design review had read. Their tests were
outside the standard suite until #91.
- `513200de` computes the Frangi fiber target in the training step, on the GPU, and `9c1e8722` computes it in
  float64. They add `core/frangi_torch.py`.
- `7b9b7190`: loader workers exit without finalizing the interpreter.
- `944503e6`: tests read training batches in-process, and one test runs `train()` with workers.
- `b1cba4c7`: each run draws its training crops from its sampling seed.

Also in scope: the validation pass's topology-threshold search, which the Frangi change sits beside.

## What changed

- **The topology-threshold search reports the evaluations it dropped.**
  - `select_topology_threshold` chooses the threshold at which the topology metrics are scored. It caught any
    `compute_centerline_dice` failure and passed over it.
  - A metric that failed on every patch therefore returned the fallback threshold and a score of 0, exactly as if
    every prediction were empty, without a word.
  - The validation pass's own topology metrics count and print their failures (`validation_diag`). The search now
    prints its first three failures and a count of what it dropped. Its result is unchanged.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P4 | **The topology-threshold search dropped failed evaluations silently**, and a metric that always failed looked like an empty prediction. | Printed and counted. Test: a metric that raises gives the fallback and both warnings. It fails on main. |

## Reviewed and sound

- **The Frangi target is the loader's, computed elsewhere.**
  - `fiber_target` takes the Frangi vesselness of `x_raw`, the whole read with its margins and before the depth
    crop, mixup or any augmentation, as the loader did. Then the per-patch min-max applies as before.
  - Each patch has its own `gamma`, as skimage computes it for one image.
  - The closed-form eigenvalues handle a repeated eigenvalue (`p = 0` gives three equal roots) and order them by
    magnitude as skimage does. `test_frangi_torch` compares the filter with skimage patch by patch; 13 pass here and
    one skips without a GPU.
  - In float64 the cost is small. At the configuration's batch size of 4, a 24 × 64 × 64 read is about 3 MB a
    tensor; at the templates' largest batch, 24, about 20 MB. So the VRAM gate, calibrated before the change, is not
    affected.
- **Workers exit without finalizing.**
  - `os._exit(0)` is registered as an exit handler before the worker's init runs. Exit handlers run last-in,
    first-out, so it runs after every handler registered later.
  - A worker's output is not lost: multiprocessing's bootstrap flushes stdout and stderr before the worker exits,
    and `os._exit` skips only the finalization after it.
  - Forcing the exit code to 0 hides almost nothing. PyTorch's SIGCHLD check reports a worker that exits nonzero or
    dies by signal. The handler is registered only inside the worker loop, so a worker that cannot unpickle its
    dataset still exits nonzero; a signal is unaffected. Errors after that, its init's included, reach the parent
    through the result queue, which `_worker_loop` sends them to.
- **Crops follow the run's sampling seed.**
  - Training entries draw their crop from `RandomState(i + seed)`, and UA-MT's from `seed + 1`. Validation keeps its
    fixed seed of 42, so the scored sample does not move.
  - The recorded `train_sampling_seed` reproduces a run's crops as well as its order.
- **Tests read in-process unless they ask for workers** (`AUTORESEARCH_LOADER_WORKERS=0` in `tests/conftest.py`).
  `test_loader_workers` runs `train()` with two workers to its first batch, and fails if the batch is read
  in-process.

## Observations for the owner (not changed)

- **The noise tolerance was measured before this change, and before protocol v2.**
  - `F1_NOISE_TOLERANCE` (3e-2) comes from four identical-config runs on 2026-07-12 (σ = 0.0120).
  - Those runs differed in batch order only, since every entry had the same crop in every run. Since `b1cba4c7`
    runs also differ in which pixels they train on: about 75% of the ink per run, against 75% fixed before.
  - Run-to-run variance can only have grown, so a tolerance set for a 5% false-promotion rate now allows more.
  - The 2026-10-12 review already recorded that the tolerance must be re-measured under protocol v2
    (`scripts/f1_noise_probe.py`). This is a second reason. The tolerance is the owner's decision.
- **The ablation's `--seed` does not fix a run's data.** `train_with_new_augs.py --seed` seeds torch, NumPy and
  `random`, but `train()` draws its sampling seed from `os.urandom`, and that seed sets the order and, since
  `b1cba4c7`, the crops. The ablation's seeds are independent replicates, not reproducible runs; its docstring's
  "pins torch / numpy / random seeds" is true but suggests more.
- **The project's test and lint tools are not declared.**
  - `pyproject.toml` lists neither `pytest`, `ruff` nor `mypy`. `pytest` reaches `uv.lock` only as another
    package's dependency, and `ruff` and `mypy` not at all.
  - So a fresh environment lacks them. The owner's last two review reports could not run Ruff or mypy, and
    pre-commit's mypy hook (`uv run --no-sync mypy`) needs mypy installed by hand.
  - A `[dependency-groups] dev` would fix this, but changes `uv.lock`. The loop's next `uv run` on the GPU host would
    then install the new packages before a cycle, so it is left to the owner.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `102f20bc` (#91), whose tree is `b1541e51`'s but for its review doc's result
  lines. It was 42 failed, 2432 passed, 21 skipped, 1 xfailed, 2 errors. The failures and errors are environmental:
  no scroll data, no CUDA, no villa data files.
- Branch: running at this commit; recorded in the next.
- `tests/test_topology_threshold.py`: 5 passed; the new test fails on main.
- Ruff (check and format) on the changed files: clean.

New test: `tests/test_topology_threshold.py::test_failed_metric_evaluations_are_reported`.
