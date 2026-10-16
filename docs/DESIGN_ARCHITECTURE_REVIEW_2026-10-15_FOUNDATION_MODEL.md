# Design and architecture review — starting from a foundation model

Date: 2026-10-15. Baseline: `4a8b4818` (main after #85). Villa pin unchanged. #86 was merged at its first head; the
review's fixes follow in a second PR, from `d67c942f`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `train.py` starts a model from a pretrained checkpoint (`foundation_model_path`), set against villa's
own LeJEPA fine-tune loader (`TrainFineTuneLEJEPA`), which reads the same checkpoints. Also the operator script
that snapshots the loop's candidates.

## What changed

- **A requested foundation model is loaded, or the run stops.** `load_foundation_model` is used by `train()` whenever
  `foundation_model_path` is set.
  - A missing file raises `FileNotFoundError`. It is checked with the label files, first in `train()` and in the
    `--smoke` preflight (`check_foundation_model_path`), so it fails in seconds. It used to be skipped without a
    word.
  - An unreadable file raises, and so does a checkpoint that holds no state dict (`TypeError`). They used to be a
    printed warning.
  - Too few fitting tensors raise `ValueError`.
    - For a LeJEPA encoder, too few means under 90% of PrimusNetwork's `shared_encoder`
      (`FOUNDATION_ENCODER_MIN_FRACTION`). An encoder of another size, such as pretraining's default "M" in
      `LeJEPAUNet`'s "S", fits only its patch-embedding stem: 70 of 280 tensors.
    - For any other model, too few means none.
    - Either case used to be a printed line.
  - In all these cases the run then trained from random weights under the experiment's name, unless a warm start from
    `best_model.pt` applied.
- **`foundation_encoder_state` maps a LeJEPA checkpoint as villa does.**
  - It removes the wrapper prefixes: DDP's `module.` and `torch.compile`'s `_orig_mod.`.
  - It takes `encoder.*` and `shared_encoder.*` by their prefix only.
  - It leaves out the rest, such as the projector.
  - `tests/test_load.py`, which ran the same mapping on the real checkpoint, now uses it.
- **The checkpoint is read on the CPU.** It can hold optimizer state, and it was read onto the GPU.
- **`load_shape_compatible_state` returns how many tensors it loaded.** `scripts/smoke_test.py`'s check that
  `best_model.pt` loads now uses that count. Its old check could not fail. It now reads "Loaded 288/288".

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P4 | **A run asked to start from a foundation model could train from scratch under its name.** `train()` skipped a missing `foundation_model_path` without a message, caught any failure to load as a printed warning, and went on when no tensor fit. Its LeJEPA mapping also differed from villa's. It took only `encoder.*` keys, removed `"encoder."` wherever it occurred, and kept DDP and compile prefixes. For the checkpoints villa writes this changed nothing: villa's saver removes those wrappers, and PrimusEncoder's names hold no nested `encoder.`. The real change is the raising. The path is dormant in the loop: the loop leaves out `lejepa_unet`, every tracked config has `foundation_model_path: null`, and `launch_finetune_lejepa.py` uses villa's trainer. | The loader stops the run instead, and maps as villa does. Tests cover: the mapping of wrapped, nested, `shared_encoder` and projector keys; in the loader, a missing file, a full load, a partial and an empty one, an unreadable file and a non-dict checkpoint; and in `train()`, a missing path stopping it before the validation catalogue is built, and a checkpoint with no fitting tensor stopping it at the model. New helpers. The two `train()` tests fail if the old call site or the early check is restored. |

## Review of #86, and what the follow-up changed

The owner reviewed #86 on the GPU host, which has the LeJEPA checkpoint, and merged it. The independent review's
fixes, below, follow in a second PR.


| Finding | Outcome |
| --- | --- |
| The tests covered the helpers but not `train()`'s call site. Restoring the old guard and `try`/`except`, or swallowing `torch.load`'s errors, left them passing. | Two `train()` tests (stubbed data; the optimizer ends the run), both checked against those reversions. The unreadable file is tested. |
| "No tensor fits" is a low floor. An "M" LeJEPA encoder in `LeJEPAUNet`'s "S" fits 70 of 280 tensors, the patch-embedding stem only, and trained on. The owner's run on the GPU host confirms it for the project's own checkpoint (`checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth`, 348 encoder tensors): into `LeJEPAUNet` (16 × 64 × 64) it loads 70 of them and changes 70 of the 280 `shared_encoder` tensors (68 missing, 210 of another shape). | A LeJEPA encoder must fill 90% of `shared_encoder`. Tested with a partial load. A run started from the project's checkpoint with `lejepa_unet` now stops, naming the 70 of 280, instead of training a mostly random encoder under the foundation's name. |
| The doc called `launch_finetune_lejepa.py` sound. The villa trainer it drives keeps the failure modes this change removes. | Recorded below. |
| A missing path was found late, after the validation catalogue, the model and the loaders, and the `--smoke` preflight never checked it. | Checked with the label files, in both. |
| A non-dict checkpoint failed with an `AttributeError`. The checkpoint was read onto the GPU. `smoke_test.py`'s tensor check could not fail. `test_load.py` imported `train.py` before its `importorskip`. | A `TypeError` names it; read on the CPU; the count is checked; the import moved. |
| The doc overstated the mapping change, and its notes on the loop and the snapshot script were loose. | Corrected. |

## Observations for the owner (not changed)

- **Villa's `TrainFineTuneLEJEPA`, which `launch_finetune_lejepa.py` drives, still trains from scratch with a
  warning** in three cases:
  - the checkpoint is missing;
  - it cannot be read. Its `torch.load` uses PyTorch's default `weights_only=True`, so a checkpoint holding any
    object it does not allow lands here too;
  - no layer loads.

  The launcher refuses only when it finds no checkpoint at all. A fix belongs upstream.
- **A loop config with `foundation_model_path` set would now stop each cycle** if the file went missing, or did not
  fit the model (a LeJEPA checkpoint with the loop's `resenc_unet`, say), although the warm start from
  `best_model.pt` follows and overwrites it whenever the architectures match. No config sets it, and the loop's
  architecture family leaves out `lejepa_unet`. Under the noise probe's strict warm start, the foundation weights are
  overwritten in full.
- **Villa's loader also accepts `shared_decoder.*` when asked** (`load_decoder_from_pretrain`). `train.py` loads the
  encoder only, as before.
- **`LeJEPAUNet` does not match the project's LeJEPA checkpoint.**
  - It builds a "S" encoder ("Match pretraining", `vesuvius_model.py`). The checkpoint's 348 encoder tensors fill
    only its stem: 70 of 280, as the owner measured on the GPU host.
  - Villa's pretraining defaults to "M" unless told otherwise.
  - Using the checkpoint would need `LeJEPAUNet` built to its size. That is the owner's call; the 90% floor makes the
    mismatch stop a run rather than pass unseen.

## Reviewed and sound

- **`scripts/snapshot_loop_candidates.sh`** polls `last_model.pt`'s modification time every 20 s and copies it 5 s
  after it sees a change. `train.py` writes that file atomically on every cycle, promoted or not
  (`DESIGN_ARCHITECTURE_REVIEW_2026-10-14_CYCLE_CHECKPOINTS.md`), so each copy is a complete candidate.
- **The mapping matches villa's.** On villa's real LeJEPA layout (`encoder` plus `projector`, 282 keys), the reviewer
  found that `foundation_encoder_state` maps exactly the 280 keys of `shared_encoder`, unwrapped or under any
  wrapper. The loaded set is the same as villa's.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `7d68d8fc` (#85), whose tree is `4a8b4818`'s but for its review doc's result
  lines. It was 42 failed, 2189 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are environmental:
  no scroll data, no CUDA, no villa data files.
- Branch, first head: 42 failed, 2191 passed, 15 skipped, 1 xfailed, 2 errors.
- Follow-up PR (from `d67c942f`): 42 failed, 2193 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 2 extra passes over #86's head are the `train()` tests.
  `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped; its `best_model.pt` check now reads 288 of 288 loaded.
- Ruff (check and format) and mypy on `train.py`: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- `test_a_lejepa_checkpoint_maps_by_prefix_as_villa_maps_it` (new helper);
- `test_a_foundation_model_that_does_not_load_stops_the_run` (new helper);
- `test_train_stops_at_once_on_a_missing_foundation_model` (fails on main);
- `test_train_stops_on_a_foundation_model_that_does_not_fit` (fails on main).

`tests/test_load.py` skips here: the LeJEPA checkpoint (`checkpoints/lejepa_foundation_v1/`) is not in this
environment.

Not verified here: a run with a real LeJEPA checkpoint.
