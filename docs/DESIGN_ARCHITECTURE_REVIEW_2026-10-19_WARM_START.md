# Design and architecture review — the warm start each cycle fine-tunes from

Date: 2026-10-19. Baseline: `503b5fcc` (main after #132), merged with `00ef31a9` (#131, #133), which do not touch
this code.
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
    which `ExperimentConfig` does not have, and the `AttributeError` was the warning. `89a1d720` replaced the field
    with `use_ridges` and left the `except`, with a comment recording the incident.
  - The block is now `train.warm_start`. It raises where the `except` swallowed:
    - a file that does not load, named with the remedy;
    - one that is not a checkpoint dictionary with a config;
    - one whose architecture matches but that holds no `model_state_dict`;
    - any error in the comparison or the load.
  - It also raises on a file that records this architecture but shares no tensor with the model. Main started
    such a run fresh, but the case has no design behind it. It is `d3da171`'s kind of bug, a module renamed or a
    prefix such as `module.` on every name. The independent review found this.
  - It now runs straight after the foundation model, before the loaders, their workers and wandb start. The run
    exits nonzero in seconds, and the loop records the cycle as `CRASHED`, with the error as the last log line. A
    crash leaves the family weights as they were.
  - Where main started from the model as built by design, it still does: no `best_model.pt`, or another
    architecture.
    - A bare state dict still starts from the model as built: it records no architecture.
    - The fresh-start message keeps its form. Where the checkpoint does not record a field, it now says "not
      recorded"; main printed `None->`.
  - The strict path the noise probe uses is `warm_start(strict=True)`, unchanged in what it loads and refuses.
- **The run records its warm start.** `run_result.json` gains `warm_start`, with three fields:
  - `loaded`: how many of the model's tensors (its state entries, buffers included) came from `best_model.pt`;
  - `model_tensors`: how many the model has;
  - `reason`: why none did, when none did.
- **The loop writes it into the sprint log** when a run did not start wholly from the incumbent, and prints it:
  `- **Warm start**: 0 of the model's 288 tensors from best_model.pt (another architecture, use_ridges:
  True->False)`. A complete load, a result without the field, or a malformed one, adds nothing.
- **The incumbent is read on the CPU**, as the strict path reads it.
  - It was read onto the GPU (`map_location=device`), into a local of `train()` that held it until the run's end.
  - So about 39 MiB of incumbent sat beside the model through training, and counted in `peak_vram_mb`. That
    figure, in `results.tsv`, `run_result.json` and the sprint log, drops by about that much from this change on.
    The loop's VRAM gate is a complexity estimate, and does not read it.
  - The model's weights keep their device and dtype: `load_state_dict` copies into them.
- **Comments.** The loop's pinning comment pointed at train.py's `arch_match` check, which no longer exists. It now
  names `train.warm_start`.
- **Tests** (`tests/test_autoresearch_measurement.py`, 8 new, 19 cases). They use a model with buffers, as the real
  ones have, so counting parameters instead of state entries fails. They cover:
  - a matching incumbent, which loads in full, and a partial load, with the counts recorded;
  - the strict path, which records a full load and refuses a partial one;
  - each "starts from the model as built" case, with its reason;
  - each incumbent that cannot be used, which raises, the shared-nothing and prefixed cases included;
  - the `d3da171` shape: a compared field the config lacks raises, not warns;
  - the CPU read;
  - `train()` itself, stopping on an unreadable `best_model.pt` in its working directory before any loader is
    built, and starting as before without one;
  - the wiring of `run_result.json`'s `warm_start` to the record `warm_start` returns, from `train()`'s source.
    The end of `train()` needs CUDA and data, as for the result's other fields.
  - the loop's sprint-log line, for:
    - none loaded;
    - some loaded;
    - all loaded;
    - no field;
    - a malformed field, a string count and a boolean one.

  With main's code, 14 of the 19 fail. `train()`'s own test fails because main reaches the optimizer. The 5 that
  pass are the loop's cases that add no line.

## Verified, no change needed

- **The tracked `best_model.pt` warm-starts in full** against `config.json`:
  - all seven `WARM_START_FIELDS` are recorded and match;
  - it loads 288 of 288 tensors.
- **`multi_task_heads` tweaks** load what fits. The loop toggles it on `resenc_unet`, and the incumbent has heads.
  - Turning them off loads 276 of 276 tensors: a full load of the smaller model, with the incumbent's 12 head tensors
    unused, so no sprint-log line.
  - A partial load would come from turning heads on over an incumbent without them.
- **The loop checks the incumbent before every cycle.**
  - `check_incumbent` reads `best_model.pt` at startup and before each cycle after the first, and refuses one that
    does not load or is not comparable.
  - `train.py` refuses to promote over such a file.
  - What it does not check is the file's `config` or `model_state_dict`: any dictionary with a protocol and a finite
    `val_f1` passes.

  So the swallowed cases that remain are a checkpoint missing those, and a bug in the warm start itself. The bug is
  the case that happened.
- **The other callers of `train.train`** are unaffected:
  - The noise probe uses the strict path, which already raised.
  - The ablation's cells warm-start from the checkout's `best_model.pt`, as the loop's do. The ablation refuses to
    start without one, so a cell that could not use it was not the measurement it reports.
- **Every checkpoint writer** saves `config: asdict(config)` with `model_state_dict`, the independent review found:
  - the promotion and `last_model.pt`;
  - the learning-curve snapshots;
  - `reevaluate_best_model.py --update-stored`.

  None writes a file this now refuses.

## Observations for the owner (not changed)

- **Whether a fresh start should run at all is left as it was.** With the architecture pinned, a cycle that starts
  from none of the incumbent ("another architecture") cannot be promoted in practice. It also wears its family's
  weight down like a real non-improvement. It is now in the sprint log. Whether such a cycle should be refused, or
  kept out of the bandit's decay, is a decision about the search. So is whether a partial load should need a
  minimum share of the model, as the foundation model's does.
- **The preflight does not warm-start.** The loop's `--smoke` preflight builds the model and runs one step, but
  does not read `best_model.pt`. A bug in the warm start now stops each cycle within seconds of its start rather
  than within the preflight.
- **The foundation model and the warm start.** With `foundation_model_path` set and a matching `best_model.pt`, the
  warm start overwrites the foundation weights, as `train.py`'s comment says. `warm_start` counts only what came
  from `best_model.pt`.
- **The ablation does not report its cells' warm starts.** Each cell's `run_result.json` now carries the record.

## Verification

Environment: CPython 3.10 venv, CPU only.

- `pytest tests/test_autoresearch_measurement.py`: 117 passed. With main's `train.py` and loop: 14 failed, 103
  passed.
- `test_noise_probe_contracts`, `test_task_heads`, `test_loader_workers`, `test_training_data_sources`,
  `test_training_step_contracts`, `test_loop_lifecycle`, `test_ablation_harness_isolation` and the suite guard,
  with the module above: all pass.
- **Mutation check.** Each mutation fails at least one test:
  - the `warm_start` key dropped from the result;
  - the strict path recording no load;
  - counting parameters;
  - no raise on a matching architecture that loads nothing;
  - no wrap of the read;
  - the GPU read;
  - `strict` not passed;
  - the call left after the loaders;
  - a broad `except` put back around it;
  - booleans taken as counts.
- `scripts/smoke_test.py`: 9 passed, 2 skipped (unchanged).
- The tracked `best_model.pt` against `config.json`, with heads on and off, above.
- Ruff and mypy clean on the changed files.
- **Independent review** of the first commit. It found:
  - the matching architecture that loads nothing;
  - the `multi_task_heads` claim, which this doc first got wrong;
  - that the result's wiring, the strict record and the tensor count were untested;
  - the `peak_vram_mb` shift;
  - that the read's error did not name the file;
  - that the raise came after the loaders;
  - the doc's account of `check_incumbent` and of `89a1d720`;
  - booleans taken as counts.

  All are addressed above, except a warm start in the preflight (an observation).
- The standard suite: see the PR.
