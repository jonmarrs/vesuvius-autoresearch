# Design and architecture review — starting from a foundation model

Date: 2026-10-15. Baseline: `4a8b4818` (main after #85). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `train.py` starts a model from a pretrained checkpoint (`foundation_model_path`), set against villa's
own LeJEPA fine-tune loader (`TrainFineTuneLEJEPA`), which reads the same checkpoints. Also the operator script
that snapshots the loop's candidates.

## What changed

- **`load_foundation_model` loads a requested foundation model, or stops the run.** It is used by `train()` whenever
  `foundation_model_path` is set.
  - A missing file raises `FileNotFoundError`. It used to be skipped without a word.
  - A checkpoint that cannot be read raises. It used to be a printed warning.
  - A checkpoint none of whose tensors fit the model raises `ValueError`. It used to be a printed line.
  - In each of those cases the run then trained from random weights under the experiment's name.
- **`foundation_encoder_state` maps a LeJEPA checkpoint as villa does.**
  - It removes the wrapper prefixes: DDP's `module.` and `torch.compile`'s `_orig_mod.`.
  - It takes `encoder.*` and `shared_encoder.*` by their prefix only.
  - It leaves out the rest, such as the projector.
  - `tests/test_load.py`, which ran the same mapping on the real checkpoint, now uses it.
- **`load_shape_compatible_state` returns how many tensors it loaded.**

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P4 | **A run asked to start from a foundation model could train from scratch under its name.** `train()` skipped a missing `foundation_model_path` without a message, caught any failure to load as a printed warning, and went on when no tensor fit. Its LeJEPA mapping also differed from villa's. It took only `encoder.*` keys and removed `"encoder."` wherever it occurred (`str.replace`), not only as the prefix. So a DDP or compiled checkpoint (`module.encoder.…`) loaded nothing, and a name with a nested `encoder.` would have been mangled. The path is dormant in the loop: the loop leaves out `lejepa_unet`, no config sets `foundation_model_path`, and `launch_finetune_lejepa.py` uses villa's trainer. | The loader stops the run instead, and maps as villa does. Tests: the mapping of wrapped, nested, `shared_encoder` and projector keys. A missing file and a checkpoint with no fitting tensor stop the run. A wrapped LeJEPA checkpoint loads into `shared_encoder`, and any other model loads by name. New helpers. |

## Observations for the owner (not changed)

- **A loop config with `foundation_model_path` set would now stop each cycle if the file went missing.** No config
  sets it, and the loop's architecture family leaves out `lejepa_unet`. The warm start from `best_model.pt` follows
  the foundation load and overwrites it whenever the architectures match.
- **Villa's loader also accepts `shared_decoder.*` when asked** (`load_decoder_from_pretrain`). `train.py` loads the
  encoder only, as before.

## Reviewed and sound

- **`scripts/snapshot_loop_candidates.sh`** copies `last_model.pt` when its modification time changes, 5 s after the
  change. `train.py` writes that file atomically on every cycle, promoted or not
  (`DESIGN_ARCHITECTURE_REVIEW_2026-10-14_CYCLE_CHECKPOINTS.md`), so each copy is a complete candidate.
- **`launch_finetune_lejepa.py`** writes a runner that drives villa's `TrainFineTuneLEJEPA` with the checkpoint it
  finds. It does not go through `train.py`, so it is not affected.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `7d68d8fc` (#85), whose tree is `4a8b4818`'s but for its review doc's result
  lines. It was 42 failed, 2189 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are environmental:
  no scroll data, no CUDA, no villa data files.
- Branch: 42 failed, 2191 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) and mypy on `train.py`: clean.

New tests in `tests/test_autoresearch_measurement.py` (new helpers):
- `test_a_lejepa_checkpoint_maps_by_prefix_as_villa_maps_it`;
- `test_a_foundation_model_that_does_not_load_stops_the_run`.

`tests/test_load.py` skips here: the LeJEPA checkpoint (`checkpoints/lejepa_foundation_v1/`) is not in this
environment.

Not verified here: a run with a real LeJEPA checkpoint.
