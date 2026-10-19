# Design and architecture review — the warm start each cycle fine-tunes from

Date: 2026-10-19. Baseline: `503b5fcc` (main after #132).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `scripts/training/train.py` starts its model from `best_model.pt`, and what the loop records about it.
- The loop pins the architecture fields (`run_autoresearch_loop.py`'s "PINNED-TO-PRODUCTION") so that every cycle is
  a fine-tune of the incumbent. A cycle that starts from the model as built cannot catch up in its budget, so it
  reverts.
- This round followed the loop's broad `except` sites, swept for a failure that is swallowed and also left out of
  the record. Most were handled by earlier reviews. This one was not.

## What changed

- **A `best_model.pt` that could not be used trained from the model as built, and the record did not say so.**
  - The lenient warm start was one `try` block whose `except Exception` printed `Warning: Could not load best
    model: …` and went on. The run then trained from random weights, or from the foundation model if one was set.
  - It reverted like any other cycle. Its sprint-log entry, `run_result.json` and `results.tsv` read as an
    ordinary non-improvement.
  - This is how `d3da171` (2026-05-06) stopped every cycle warm-starting for 11 days. It compared `in_channels`,
    which `ExperimentConfig` does not have, and the `AttributeError` was the warning. `89a1d720` removed the field
    and left the `except`, with a comment recording the incident.
  - The block is now `train.warm_start`, which raises where the `except` swallowed:
    - a file that does not load;
    - one that is not a checkpoint dictionary with a config;
    - one whose architecture matches but that holds no `model_state_dict`;
    - any error in the comparison or the load.

    It raises before the optimizer is built. The run then exits nonzero, and the loop records the cycle as
    `CRASHED`, with the run's last log line. A crash leaves the family weights as they were.
  - Where main started from the model as built and said so, it still does: no `best_model.pt`, another
    architecture, or no tensor whose name and shape match. A bare state dict still starts from the model as built:
    it records no architecture. The fresh-start message keeps its form, and names a field the checkpoint does not
    record as not recorded, where main printed `None->`.
- **The run records its warm start.** `run_result.json` gains `warm_start`, with three fields:
  - `loaded`: how many of the model's tensors came from `best_model.pt`;
  - `model_tensors`: how many tensors the model has;
  - `reason`: why none did, when none did.

  The strict path the noise probe uses records a complete load.
- **The loop writes it into the sprint log** when a run did not start wholly from the incumbent, and prints it:
  `- **Warm start**: 0 of the model's 288 tensors from best_model.pt (another architecture, use_ridges:
  True->False)`. A complete load, and a result without the field, add nothing.
- **The incumbent is read on the CPU**, as `load_required_starting_checkpoint` reads it. It was read onto the GPU
  (`map_location=device`), beside the model it is copied into. On a card another job is using, that read could fail
  where the CPU read does not, and the failure was swallowed.
- **Comments.** The loop's pinning comment pointed at train.py's `arch_match` check, which no longer exists. It now
  names `train.warm_start`.
- **Tests** (`tests/test_autoresearch_measurement.py`, 7 new, 15 cases):
  - a matching incumbent loads, and so does a partial one, with the counts recorded;
  - each "starts from the model as built" case, with its reason;
  - each incumbent that cannot be used, which raises;
  - the `d3da171` shape: a compared field the config lacks raises, not warns;
  - the CPU read;
  - `train()` itself, stopping on an unreadable `best_model.pt` in its working directory, and starting as before
    without one;
  - the loop's sprint-log line, for:
    - none loaded;
    - some loaded;
    - all loaded;
    - no field;
    - a malformed field.

  With main's code, 11 of the 15 fail; `train()`'s fails because main reaches the optimizer. The 4 that pass are
  the loop's cases that add no line.

## Verified, no change needed

- **The tracked `best_model.pt` warm-starts in full** against `config.json`:
  - all seven `WARM_START_FIELDS` are recorded and match;
  - it holds 288 tensors.
- **The loop cannot start over an unreadable incumbent.**
  - `check_incumbent` reads `best_model.pt` before the first cycle, and refuses one that does not load.
  - `train.py` refuses to promote over such a file.

  So the swallowed case was what is left: a file that changes mid-shift, or a bug in the warm start itself, which
  is the case that happened.
- **The other callers of `train.train`** are unaffected:
  - The noise probe uses the strict path, which already raised.
  - The ablation's cells warm-start from the checkout's `best_model.pt`, as the loop's do. The ablation refuses to
    start without one, so a cell that could not use it was not the measurement it reports.
- **`multi_task_heads` tweaks** still load what fits. The loop toggles it on `resenc_unet`, which changes the heads,
  not the backbone. Such a cycle records a partial load: some of the model's tensors are new.

## Observations for the owner (not changed)

- **Whether a fresh start should run at all is left as it was.** With the architecture pinned, a cycle that starts
  from none of the incumbent ("another architecture", "no tensor fits") cannot be promoted in practice. It also
  wears its family's weight down like a real non-improvement. It is now in the sprint log. Whether such a cycle
  should be refused, or kept out of the bandit's decay, is a decision about the search.
- **The foundation model and the warm start.** With `foundation_model_path` set and a matching `best_model.pt`, the
  warm start overwrites the foundation weights, as `train.py`'s comment says. `warm_start` counts only what came
  from `best_model.pt`.
- **The ablation does not report its cells' warm starts.** Each cell's `run_result.json` now carries the record.

## Verification

Environment: CPython 3.10 venv, CPU only.

- `pytest tests/test_autoresearch_measurement.py`: 113 passed. With main's `train.py` and loop: 11 failed, 102
  passed.
- `test_noise_probe_contracts`, `test_task_heads`, `test_loader_workers`, `test_training_data_sources`,
  `test_training_step_contracts`, `test_loop_lifecycle`, `test_ablation_harness_isolation` and the suite guard,
  with the module above: 280 passed.
- `scripts/smoke_test.py`: 9 passed, 2 skipped (unchanged).
- The tracked `best_model.pt` read against `config.json`, above.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR.
