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

- **The topology-threshold search records the evaluations it dropped.**
  - `select_topology_threshold` chooses the threshold at which the topology metrics are scored. It caught any
    `compute_centerline_dice` failure and passed over it.
  - A metric that failed on every patch gave the fallback threshold and a score of 0, as an all-NaN one does,
    without a word. (An all-empty prediction is different: villa scores it 0.0, so it selects the first candidate.)
  - The validation pass's own topology metrics count their failures in `validation_diag`, which `run_result.json`
    and the checkpoint record. The search now prints its first three failures and a count, and records the count
    there as `topology_threshold_errors`. Its result is unchanged.
- **Comments that still described the loader's Frangi target** (`run_autoresearch_loop.py`'s
  `target_fiber_source` template, two in `vesuvius_loader.py`) now say that `train.py` computes it from the batch.
- **A test checks `frangi_torch` against skimage at a Frangi scale of 1.**

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P4 | **The topology-threshold search dropped failed evaluations silently.** A metric that always failed looked like an all-NaN one, and nothing was recorded. | Printed (the first three), counted, and recorded in `validation_diag`. Test: a metric that raises gives the fallback, exactly three printed failures, the count, and the recorded count. It fails on main. |
| P4 | Three comments described the Frangi target as the loader's, at ~86 ms a patch. | Corrected. |

## Review of the PR, and what it changed

The independent review of the PR's first head (`5ea56977`) found nothing blocking. It confirmed the code change
and the review's conclusions on the five commits, and measured what the doc had only estimated.

| Finding | Outcome |
| --- | --- |
| The noise-tolerance observation had its history wrong. The July runs did not differ in order: the loader had no sampler then, so all four read the same crops in raster order. The protocol is v3 now (`ff13ee15`), not v2. | Corrected below. |
| The float64 memory estimate counted one tensor; `_frangi` holds about 35 at once. Measured on the CPU: 106 MiB at batch size 4, 636 MiB at 24. Batch 24 never passes the VRAM gate at 16 layers; the largest it admits, 16, is about 0.42 GiB. | Corrected below. |
| The search's count reached only the log; the comment said it was reported as the pass's metrics are. | Recorded in `validation_diag`. |
| "As if every prediction were empty" was false: villa scores an empty prediction 0.0. The "first three" cap was untested. | Corrected; the cap is tested. |
| A skip was attributed to the missing GPU (it is for Fr47's absence). Forcing the exit code to 0 does hide one case. "Reproduces a run's crops" overstated. The 8-σ truncation differs from skimage's below a scale of 1. Some smaller claims. | Corrected below. At a scale of 1 the truncation makes no measurable difference (a new test matches skimage either way), so the filter keeps it. |

## Reviewed and sound

- **The Frangi target is the loader's, computed elsewhere.**
  - `fiber_target` takes the Frangi vesselness of the CT channel of `x_raw`, the whole read (24 slices with its
    margins), before the depth crop, mixup or any augmentation, as the loader did. It is called once per step under
    `no_grad`, and the per-patch min-max is unchanged.
  - `frangi_torch` follows skimage 0.25:
    - the sign flip for bright ridges;
    - derivative filters at σ/√2, with scipy's reflect edges;
    - eigenvalues sorted stably by magnitude, with the `1e-10` clamp;
    - `gamma` as half of each patch's largest Hessian norm;
    - `alpha = beta = 0.5`, then the mean over z.

    The closed-form eigenvalues handle a repeated eigenvalue (`p = 0`). `test_frangi_torch` compares it with skimage
    patch by patch: 14 pass here, and one skips for want of Fr47.
- **Its memory is affordable.**
  - Measured on the CPU, the filter peaks at about 106 MiB at the configuration's batch size of 4. At 16, the largest
    batch the VRAM gate admits at 16 layers, it peaks at about 0.42 GiB.
  - The peak is transient and comes before the forward pass, so it does not add to the step's activations.
  - Its GPU time has not been measured, here or in the commits.
- **Workers exit without finalizing.**
  - The loader uses spawn, so a worker ends with `sys.exit`, and its exit handlers run.
  - `os._exit(0)` is registered first, inside the worker loop (`_init_worker` is the `worker_init_fn`). Exit handlers
    run last-in, first-out, so it runs after every handler registered later.
  - Python's stdout and stderr are flushed by multiprocessing's bootstrap before that. C-level stdio buffers, and exit
    handlers registered before the init (`logging.shutdown`), are skipped; nothing in the workers needs them today.
  - **What forcing the exit code to 0 hides.** PyTorch's SIGCHLD check reports a worker that exits nonzero or dies by
    signal.
    - Still reported: a worker that cannot unpickle its dataset exits before the handler is registered, and still
      exits nonzero. A signal is unaffected.
    - Still reaching the parent: init and fetch errors, through the result queue.
    - Changed: a `BaseException` that escapes the worker loop now exits 0. The SIGCHLD check stays silent, and the
      liveness check reports "exited unexpectedly" without the code, a few seconds later. Its traceback still
      reaches stderr.
- **Crops follow the run's sampling seed.**
  - Training entries draw their read crop from `RandomState(i + seed)`, and UA-MT's from `seed + 1`.
  - These keep fixed draws: validation (seed 42), the mid-run AUC curve (its own fixed state), and
    `reevaluate_best_model` (through `build_validation_dataset`). The `--smoke` preflight is synthetic.
  - The recorded `train_sampling_seed` (in `run_result.json` and the checkpoint) rebuilds a run's crops and order
    offline. It does not reproduce the run: the model's depth window inside the read and the augmentations come from
    the unseeded global generators, and `train()` cannot be given a seed.
- **Tests read in-process unless they ask for workers** (`AUTORESEARCH_LOADER_WORKERS=0` in `tests/conftest.py`).
  `test_loader_workers` runs `train()` with two workers to its first batch, and fails if the batch is read
  in-process; 13 pass here.

## Observations for the owner (not changed)

- **The noise tolerance was measured on another protocol, and on identical batches.**
  - `F1_NOISE_TOLERANCE` (3e-2) comes from four identical-config runs on 2026-07-12 (σ = 0.0120,
    `reports/detector/f1_noise_probe.json`).
  - Those runs had no sampler: all four read the same crops in the same raster order. Only augmentation, the depth
    window and GPU nondeterminism varied.
  - Since then:
    - runs draw their order and subset from their seed (`8f5fec94`, 10-12) and their crops from it (`b1cba4c7`,
      10-14);
    - validation is protocol v3 (`ff13ee15`, 10-14);
    - a depth band applies (10-13).
  - Run-to-run variance very likely grew, so a tolerance set for a 5% false-promotion rate probably allows more.
  - The 2026-10-12 review already asked for it to be re-measured (`scripts/f1_noise_probe.py`). It should be
    re-measured under v3. The tolerance is the owner's decision.
- **A failing GPU Frangi now stops the cycle.** The loader fell back to a zero target, with a warning, when its
  Frangi failed. An exception in the training step's (out of GPU memory, say) ends the run. The `--smoke` preflight
  runs on the CPU with a synthetic batch and does not compute the fiber target, so it cannot catch this earlier.
- **Within a run, every pass reads the same crops.** `RandomState(i + seed)` does not depend on the pass, so a run
  long enough to pass its catalogue twice sees each crop twice; only augmentation differs.
- **The ablation's `--seed` does not fix a run's data.** `train_with_new_augs.py --seed` seeds torch, NumPy and
  `random`, but `train()` draws its sampling seed from `os.urandom`, and that seed sets the order and the crops. The
  ablation's seeds are independent replicates.
- **The project's test and lint tools are not declared.**
  - `pyproject.toml` lists neither `pytest`, `ruff` nor `mypy`. `pytest` reaches `uv.lock` only through `kimimaro`,
    and `ruff` and `mypy` not at all.
  - So a fresh environment lacks them. The owner's PR #88 report could not run either, and pre-commit's mypy hook
    (`uv run --no-sync mypy`) needs mypy installed by hand; its Ruff hook brings its own.
  - A `[dependency-groups] dev` would fix this, but changes `uv.lock`. The loop's next `uv run` on the GPU host would
    then install the new packages before a cycle, so it is left to the owner.
- **The worker-abort counts in `7b9b7190` disagree:**
  - the commit says 7 of 24 stops on Fr47, and 3 of 12 without the fix;
  - `_init_worker`'s docstring says 4 of 12;
  - the test's docstring says 1 in 3.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The project pins
torch 2.9.1; the DataLoader behaviour above was read from 2.14.1's Python side and the review's probes.

- Baseline: the validation run of `102f20bc` (#91), whose tree is `b1541e51`'s but for its review doc's result
  lines. It was 42 failed, 2432 passed, 21 skipped, 1 xfailed, 2 errors. The failures and errors are environmental:
  no scroll data, no CUDA, no villa data files.
- Branch, PR first head (`5ea56977`): 42 failed, 2433 passed, 21 skipped, 1 xfailed, 2 errors. Same set; the extra
  pass is the new test. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped (no training data).
- Branch, after the PR review's fixes: running at this commit; recorded in the next.
- `tests/test_topology_threshold.py`: 5 passed; the new test fails on main. `tests/test_frangi_torch.py`: 14 passed,
  1 skipped.
- Ruff (check and format) and mypy on the changed files: clean.

New tests:
- `tests/test_topology_threshold.py::test_failed_metric_evaluations_are_reported`;
- `tests/test_frangi_torch.py::test_matches_skimage_at_a_small_scale` (a guard; it passes on main too).
