# Design and architecture review — the owner's #487, the training depth contract

Date: 2026-11-22. Baseline: `06dab63` (main after round #186's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 19:12 UTC firing on 2026-11-22. The 18:12 firing came during the usage limit that held up
round #186 and was not run on its own. Main had not moved since round #186's merge.

It takes **#487**, merged on 2026-11-22. #487 makes every training and validation read hold a full model window:
- `num_layers` must be a positive integer; the check moved to `inference_constants.positive_integer`;
- the loader's datasets take a `min_read_depth` and refuse a shorter read, through `_read_depth`;
- the trainer draws one offset that fits a full window in the labeled read and any UA-MT read, through
  `_training_windows`;
- the trainer refuses to batch volumes of different read depths together;
- validation's fixed window, through `_validation_window`, marks a short batch as incomplete.

## What changed

### Seven checks of the depth contract are now tested (`tests/test_training_data_sources.py`)

This round made 25 mutants across the loader, `inference_constants.py`, `train.py` and `config.py`. The tests of the
nine modules that reach this code killed 17, and one cannot be killed (below). Four new test functions, 9 cases, kill
the other seven:
- **The trainer's depth checks, run with explicit patch catalogs.** #487's own test of them needs villa's patch
  finder here. The new test writes a `patches.json` beside every volume, so the datasets are built without patch
  discovery, and stops the run where the loader under test would be built. It checks three things:
  - a labeled source one slice short is refused by the loader, naming the volume;
  - labeled and UA-MT sources of different depths are refused for a batch size of 2;
  - with one patch per batch, sources of different depths are accepted.
- **A read may be exactly its required depth.** With no minimum, the read is the requested depth.
- **`positive_integer` returns a Python `int`**, for a NumPy integer, and names the rule "nonnegative" when the
  minimum is 0.
- **Validation refuses a non-integer depth** set on a configuration after it was built. The configuration checks
  its depth when built, and `build_validation_dataset` checks it again.

No code changed. No defect was found.

### One mutant no test can kill

**Leaving out `min(depth - offset, ...)` in the compressed window's length.** A slice past the read's end stops at
the end. A window that already has `num_layers` slices is resized to the same size, which leaves its values
unchanged. Both versions therefore give the same tensor.

## Verified, no change needed

- **A depth band cannot shrink a read below its minimum.** `band_read_range` refuses a band, widened by its margin,
  that cannot hold the dataset's read.
- **Validation's window and its minimum agree.** Validation reads require `num_layers + 4` slices. The window starts
  at the fixed offset 4 and is `num_layers` long. `periodic_pixel_auc_eval` uses the same window.
- **A short validation batch is recorded, not scored.** `collect_validation_predictions` counts the window's
  `ValueError` as a batch error, and the diagnostics then report the run as incomplete.
- **Sources with no patches are left out of the batching comparison.** A source whose dataset is empty cannot add
  a patch to a batch, so its depth does not count. Every other labeled source must share one read depth when the
  batch size is above 1, because the shuffled loader can put patches from any two sources in one batch.
- **The training offset keeps its historic range** when the read has full context: `randint(0, 8)`, the exclusive
  upper bound `2 * DEPTH_MARGIN`.
- **The documentation matches the code.** `docs/TRAINING_DATA_IMPORT.md` says:
  - training requests up to eight extra slices;
  - the offset fits a full window in both batches;
  - batched sources need matching depths, and one patch per batch does not;
  - validation needs `num_layers + 4` slices;
  - the scorer marks a short batch incomplete.

  All five hold.

## Observations for the owner (not changed)

- **#487's own trainer-level tests need villa here.** Its three `test_real_trainer_refuses_incompatible_volume_depths`
  cases build datasets by patch discovery. The new variant reaches the same checks with catalogs, and it can run
  where villa is absent.

## Verification

- **The touched module.** `test_training_data_sources.py` gives 33 passed and 3 failed, against 24 and 3 on
  `06dab63`. The three are #487's trainer-level cases, which need villa's patch finder.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,091 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** 268 failing ids: round #186's 265 and #487's three trainer-level cases. Round #186's suite
  ran before #487 was merged; the three fail on `06dab63` as well.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,744 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `06dab63`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`train.py` and `config.py` are in `scripts/training/`**, where only tests may be added. Their #487 changes were
  mutated in the worktree to test the tests, and left as they are.
- **Still not reviewed from the owner's merges since round #182:** #447, #448, #450, #453, #456, #458, #461, #463,
  #465, #468 to #478, #480 and #483.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 25 were run again with the new tests: 24 are killed and the one above survives.
