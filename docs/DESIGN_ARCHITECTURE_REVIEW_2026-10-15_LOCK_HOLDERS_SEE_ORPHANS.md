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
going in a session of its own. #82 let `stop.sh` and `status` see such runs. The noise probe, the augmentation
ablation and the incumbent re-score hold the same lock, but they still started beside one.

## What changed

- **The ablation, the noise probe and the re-score (`--update-stored`) refuse to start beside a training run that no
  loop supervises.** After taking the lock and before running anything, each asks
  `loop_control.unsupervised_runs_refusal(repo)`, which uses the same detection as the loop's start and `status`.
  Each then names the runs and says how to stop them:
  - the ablation exits 1 before any cell, leaving `run_result.json` alone and writing no CSV;
  - the noise probe raises before creating its output directory, which its CLI reports as a usage error (exit 2);
  - the re-score raises "best_model.pt was not updated" before it settles a killed loop's hold or loads anything.

  None of them stops a run. The loop's start stops a loop's run once it is past any cycle's timeout; these leave it
  to the operator, for whom `./stop.sh` stops the runs a loop or ablation started.
- **The README** says so.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **The re-score released a killed loop's hold while that loop's run was still training.** A loop killed mid-cycle leaves `.best_model.pt.held`, and its run going. Until that run promotes, `best_model.pt` is still the held file. The loop's start therefore looks for such a run before it settles the hold (#81). `--update-stored` settled the hold without looking: `leftover_hold()` found the same file and removed the hold. If the run then promoted, during the scoring (the hash check refused to write, but the hold was gone) or after the write, the loop's next start found no hold. It kept a model, and its rows in `results.tsv` and `prize_readiness.tsv`, that no cycle had recorded. That decision is the operator's, which is what #81's hold exists to keep. The re-score is likely soon: #66's protocol v3 needs every incumbent re-scored. Found in the PR review. | The re-score asks before the hold, as the loop's start does. Test: with the hold and a killed loop's run going, the re-score refuses, and the hold and `best_model.pt` are untouched, the lock released and the run left alone. Fails on main. |
| P3 | **The ablation started beside an orphaned run.** A loop or ablation killed without its handler leaves its run training in the checkout. The ablation took the free lock and started its cells beside that run. Each cell shared the GPU, so it trained fewer steps in its fixed budget, and the conditions were compared on unequal footing. Both processes write `run_result.json` in the checkout, and the ablation reads a cell's result from there. A cell that wrote none, or the orphan finishing after the cell, could credit the cell with the orphan's result. | The ablation refuses, names the run, and leaves `run_result.json` and its CSV alone. Test: with an orphaned loop run in the checkout, no cell runs, the lock is released, and the run is named but not stopped. Fails on main. |
| P3 | **The noise probe started beside one too.** Its trials work in their own directories, and it re-checks its starting checkpoint's hash, so its records stay correct. But each trial's time budget assumes the GPU to itself. A trial sharing it trains fewer steps, which inflates the run-to-run spread the probe exists to measure. | The probe refuses before creating its output. Test: no output directory, the lock released (from another process), and the run left alone. Fails on main. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The re-score was left out, on the grounds that it refuses beside a killed loop's hold. It does so only once the run has replaced `best_model.pt`; until then it released the hold. | Given the check, before the hold. Tested (first row above). |
| The probe test checked the lock with `running_pid` in its own process. POSIX record locks do not exclude their own process, so the check could not fail. Changed to a check from another process, the test still passed when the probe raised outside its `try` and left the lock held: once `pytest.raises` returned, the traceback was dropped and the collector closed the file. | Checked from another process, while the exception (and with it the probe's frame) is still held. That mutation now fails the test. The re-score test does the same. |
| The doc said the check had to come before the caller's first run, or that run would be listed. That holds for the ablation's cells only; the probe's trials work elsewhere. | Corrected below, and in the helper's docstring. |
| The doc said `stop.sh`, like these scripts, leaves runs to the operator. It stops the runs a loop or ablation started. | Corrected above. |
| `peak_vram_mb` was said to count the training process. It is `torch.cuda.max_memory_allocated()`: PyTorch's allocator only. | Corrected below. |
| The refusal said "It shares the GPU … best_model.pt" when several runs might be listed, and an ablation's cell does not write `best_model.pt`. | Reworded. |
| The fixture would overwrite a real `scripts/training/train.py` if pointed at a checkout. Its teardown could signal a group whose leader the test had already reaped. | It refuses an existing trainer, and signals only a run not yet reaped. |
| The check sees one checkout; runs in another clone on the same GPU are not seen. | Recorded below. |

## Observations for the owner (not changed)

- **A loop's run whose `uv` was killed alone counts as started by hand (#82's review fix).**
  - `stop.sh` names it without stopping it, and the loop's start no longer stops it past any cycle's timeout.
  - The loop, the probe, the ablation and the re-score now all wait for it to end.
  - Recognising a supervisor's runs by a mark in their environment, set by `ProcessSupervisor.run` and inherited by
    each process of the run, would keep such a run counted as a loop's. #82 settled the behaviour, so it is not
    changed here.
- **The check is per checkout.** A training run in another clone or worktree on the same GPU is not seen, though it
  shares the card all the same.
- **The recorded peak VRAM leaves out the loader workers.** `peak_vram_mb` is PyTorch's allocator peak in the
  training process (`torch.cuda.max_memory_allocated()`). It counts no CUDA context or CuPy pool, in that process or
  elsewhere.
  - Since #74, each loader worker that computes the ridge channel on CuPy holds a CUDA context and a CuPy pool of its
    own on the same GPU: up to three workers.
  - At today's configuration (64 px patches, batch 4) this is small beside the card.
  - The loop's VRAM estimate, a complexity heuristic, does not count it either.
- **A noise-probe trial orphaned by a killed probe** works in the probe's staging directory, not the checkout, so no
  check sees it. It shares the GPU until its budget ends.
- **The first-use record beside the incumbent** (`best_model.pt.inputs.json`) is written in place.
  - A stop mid-write leaves a record that does not parse, and the next check records the inputs afresh.
  - Since #66, every incumbent is re-scored under v3, which stores its fingerprint in the checkpoint. So the record
    is rarely needed.

## Reviewed and sound

- **Where the check runs.**
  - It runs after the lock is taken, so no other holder can start a run meanwhile.
  - In the ablation, it runs before the first cell, which would otherwise be listed too.
  - In the re-score, it runs before the hold is settled.
  - The ablation's `--dry-run`, the probe's plan and a re-score without `--update-stored` take no lock and write
    nothing, so they are not checked.
- **The loader workers (#74)** are spawned in the run's process group, as is their `Manager`.
  - So the supervisor's stop and timeout reach them.
  - Their command lines do not name the training script, so no check counts them as runs.
  - Their warning counts reach `run_result.json` through the `Manager`.
- **The fiber target on the GPU (#75)** is computed before mixup and cutmix, which then transform it together with
  the input and the ink target, as they did the Sobel-Z target. It is computed only for a model that trains a fiber
  or QC head (`fiber_source`).
- **Each run's crops (#79)** are drawn from its sampling seed, which `run_result.json` and the checkpoint record.
- **Protocol v3 (#66).**
  - `train.py` and the re-score split the patches the same way: every scored patch is pooled for `val_f1`, and the
    per-patch diagnostics use only the ink-containing ones (`ink_containing`).
  - The protocol string decides which patches count (`scores_ink_free_patches`).
  - A v2 incumbent is refused until it is re-scored.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline (`05fd1769`): 42 failed, 2180 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are
  environmental: no scroll data, no CUDA, no villa data files.
- Branch, first head: 42 failed, 2182 passed, 15 skipped, 1 xfailed, 2 errors.
- Branch, after the PR review's fixes: 42 failed, 2183 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 3 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- The five modules these touch (`test_checkpoint_tool_contracts`, `test_noise_probe_contracts`,
  `test_ablation_harness_isolation`, `test_loop_lifecycle`, `test_autoresearch_measurement`): 248 passed, twice,
  with no process left behind.
- Ruff (check and format) and mypy on the changed files: clean.

New tests (each fails on main):
- `tests/test_ablation_harness_isolation.py::test_the_ablation_will_not_run_beside_a_run_no_loop_supervises`;
- `tests/test_noise_probe_contracts.py::test_a_run_no_loop_supervises_refuses_execution`;
- `tests/test_checkpoint_tool_contracts.py::test_a_rescore_keeps_the_hold_while_the_killed_loops_run_goes_on` (fails
  on the first head too).

They use a new fixture, `orphaned_run` (`tests/conftest.py`). It starts a run the way a supervisor does and kills its
group at teardown.

Not verified here: any of the three on the GPU host beside a real orphaned run.
