# Design and architecture review: the other lock holders and an orphaned run

Date: 2026-10-15. Baseline: `05fd1769` (main after #82, #74, #75, #79, #64, #65, #66 and #72). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- what main gained since `bc01631d`:
  - #82, with the owner's review fix;
  - the loader workers (#74);
  - the Frangi fiber target on the GPU (#75);
  - each run's training crops drawn from its sampling seed (#79);
  - validation protocol v3 (#66);
- set against the gap #82's review left open: the work that holds the checkout's lock besides the loop.

#81 made the loop refuse to start beside a training run that no loop supervises, such as a run a killed loop left
going in a session of its own. #82 let `stop.sh` and `status` see such runs. The noise probe and the augmentation
ablation, which hold the same lock, still started beside one.

## What changed

- **The ablation and the noise probe refuse to start beside a training run that no loop supervises.** After taking
  the lock and before their first run, each asks `loop_control.unsupervised_runs_refusal(repo)`, which uses the same
  detection as the loop's start and `status`. Each then names the runs and says how to stop them:
  - the ablation exits 1 before any cell, leaving `run_result.json` alone and writing no CSV;
  - the noise probe raises, which its CLI reports as a usage error (exit 2), before creating its output directory.

  Neither stops a run: like `stop.sh`, it leaves that to the operator.
- **The README** says so.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **The ablation started beside an orphaned run.** A loop or ablation killed without its handler leaves its run training in the checkout. The ablation took the free lock and started its cells beside that run. Each cell then shared the GPU, so it trained fewer steps in its fixed budget, and the conditions were compared on unequal footing. Both write `run_result.json` in the checkout, and the ablation reads a cell's result from there. A cell that wrote none, or the orphan finishing after the cell, could credit the cell with the orphan's result. The loop's start has refused beside such a run since #81. | The ablation refuses, names the run, and leaves `run_result.json` and its CSV alone. Test: with an orphaned loop run in the checkout, no cell runs, the lock is released, and the run is named but not stopped. Fails on main. |
| P3 | **The noise probe started beside one too.** Its trials work in their own directories, and it re-checks its starting checkpoint's hash, so its records stay correct. But each trial's time budget assumes the GPU to itself. A trial sharing it trains fewer steps, which inflates the run-to-run spread the probe exists to measure. | The probe refuses before creating its output. Test: no output directory, the lock released, the run left alone. Fails on main. |

## Observations for the owner (not changed)

- **A loop's run whose `uv` was killed alone counts as started by hand (#82's review fix).**
  - `stop.sh` names it without stopping it, and the loop's start no longer stops it past any cycle's timeout.
  - The loop, the probe and the ablation now all wait for it to end.
  - Recognising a supervisor's runs by a mark in their environment, set by `ProcessSupervisor.run` and inherited by
    each process of the run, would keep such a run counted as a loop's. #82 settled the behaviour, so it is not
    changed here.
- **`peak_vram_mb` counts the training process only.**
  - Since #74, each loader worker that computes the ridge channel on CuPy holds a CUDA context and a CuPy memory
    pool of its own on the same GPU: up to three workers.
  - At today's configuration (64 px patches, batch 4) this is small beside the card.
  - The loop's VRAM estimate, a complexity heuristic, does not count it either.
- **The re-score is not given the check.**
  - It refuses beside a killed loop's hold.
  - It re-checks `best_model.pt`'s hash before writing.
  - Its scores do not depend on a time budget.
  - An orphan without a hold (an ablation's cell) writes its own checkpoint, not `best_model.pt`.
- **A noise-probe trial orphaned by a killed probe** works in the probe's staging directory, not the checkout, so no
  check sees it. It shares the GPU until its budget ends.
- **The first-use record beside the incumbent** (`best_model.pt.inputs.json`) is written in place. A stop mid-write
  leaves a record that does not parse, and the next check records the inputs afresh. Since #66, every incumbent is
  re-scored under v3, which stores its fingerprint in the checkpoint, so the record is rarely needed.

## Reviewed and sound

- **Where the check runs.**
  - It runs after the lock is taken, so no other holder can start a run meanwhile.
  - It runs before the caller's first run, which would otherwise be listed too.
  - The ablation's `--dry-run` and the probe's plan take no lock and run nothing, so they are not checked.
- **The loader workers (#74)** are spawned in the run's process group, as is their `Manager`. So the supervisor's
  stop and timeout reach them. Their command lines do not name the training script, so no check counts them as runs.
  Their warning counts reach `run_result.json` through the `Manager`.
- **The fiber target on the GPU (#75)** is computed before mixup and cutmix. Those then transform it together with
  the input and the ink target, as they did the Sobel-Z target. It is computed only for a model that trains a fiber
  or QC head (`fiber_source`).
- **Each run's crops (#79)** are drawn from its sampling seed, which `run_result.json` and the checkpoint record.
- **Protocol v3 (#66).**
  - `train.py` and the re-score split the patches the same way: every scored patch is pooled for `val_f1`, and
    the per-patch diagnostics use only the ink-containing ones (`ink_containing`).
  - The protocol string decides which patches count (`scores_ink_free_patches`).
  - A v2 incumbent is refused until it is re-scored.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline (`05fd1769`): 42 failed, 2180 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are
  environmental: no scroll data, no CUDA, no villa data files.
- Branch: 42 failed, 2182 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- `tests/test_ablation_harness_isolation.py`, `tests/test_noise_probe_contracts.py` and `tests/test_loop_lifecycle.py`:
  89 passed, with no process left behind.
- Ruff (check and format) and mypy on the changed files: clean.

New tests (each fails on main):
- `tests/test_ablation_harness_isolation.py::test_the_ablation_will_not_run_beside_a_run_no_loop_supervises`;
- `tests/test_noise_probe_contracts.py::test_a_run_no_loop_supervises_refuses_execution`.

Both use a new fixture, `orphaned_run` (`tests/conftest.py`). It starts a run the way a supervisor does and kills
its group at teardown.

Not verified here: either script on the GPU host beside a real orphaned run.
