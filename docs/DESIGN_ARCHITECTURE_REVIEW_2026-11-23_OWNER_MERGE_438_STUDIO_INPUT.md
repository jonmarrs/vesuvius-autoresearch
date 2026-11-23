# Design and architecture review — the owner's #438, the Studio input exporter

Date: 2026-11-23. Baseline: `2f3a788` (main after round #191's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:12 UTC firing on 2026-11-23. Main had not moved since round #191's merge.

It takes **#438**, which adds `scripts/prepare_studio_input.py`. The exporter writes 16 consecutive planes of a local
render, cropped and in the caller's depth order, as the uint8 `[16, H, W]` array the Studio reader takes, with an
`input.json` of hashes. Before any codec is built, it accepts only:
- a local `.npy` file or Zarr v2 directory;
- canonical uint8 metadata with no filters;
- raw or standard Blosc compression.

It reads in bounded blocks and writes only into a new directory. `docs/STUDIO_INPUT_PREPARATION.md` is its guide.

## What changed

### Fifteen more guards of the exporter are tested

This round made 32 mutants of the exporter. #438's tests killed 17. Six new test functions, 15 cases, kill the other
15.

In `tests/test_prepare_studio_input_zarr.py`:
- **Each Blosc setting is checked on its own.** From an otherwise valid Blosc compressor, each of these is refused
  before Zarr is called:
  - another codec id;
  - an extra key;
  - a numeric `cname`;
  - `clevel` 10;
  - a boolean `shuffle` or `shuffle` 3;
  - a float `blocksize` or `blocksize` −1.

  #438's cases each broke several rules at once, so removing any one rule left them refused.
- **A decoded chunk exactly at the block limit is accepted**: 24 bytes against a limit of 24.

In `tests/test_prepare_studio_input.py`:
- **A plan is refused with its own reason**: a two-plane depth step that stays inside the source, and a zero block
  limit. #438's plan test matches any `ValueError`, so a mutant that refused for another reason still passed.
- **A three-dimensional source that is not uint8 is refused as such**, rather than at the later block check.
- **A payload and an output row exactly at their limits are accepted**: 320 bytes, and a 5-byte row.
- **A source block of the wrong shape is refused**, and nothing is left behind.

No code changed. No defect was found.

## Verified, no change needed

- **The checked metadata is the metadata Zarr uses.** The reader overlays the validated `.zarray` bytes on the
  directory store, so a codec change after the check is not read. #438's test covers it.
- **The output is always new.** `mkdir` refuses an existing directory and a dangling link. On failure only the files
  this run created are removed, then the directory. Neither is deleted recursively.
- **The guide matches the code.** `docs/STUDIO_INPUT_PREPARATION.md` gives:
  - the accepted formats;
  - the check before codec construction;
  - half-open crops;
  - steps of ±1 only;
  - new output directories only.

  All hold.

## Observations for the owner (not changed)

- **A missing Zarr chunk is read as zeros.** Zarr fills an absent chunk with the fill value, so a render with a
  missing chunk inside the crop exports a block of zeros and hashes it. Some writers leave all-zero chunks out on
  purpose, so refusing every absent chunk would refuse valid renders. The guide does not mention this.
- **A cut-short Blosc chunk is not checked.** #400 found that such a chunk can decode to a full chunk of the wrong
  bytes, and `repro/sota_data/pyramid_depth.py` now checks each frame against its header. This exporter accepts Blosc
  and does not.

## Verification

- **The touched modules.** `test_prepare_studio_input.py` gives 36 passed, against 30 on `2f3a788`, and
  `test_prepare_studio_input_zarr.py` gives 31, against 22.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    two changed test files.
  - Mypy is clean over the whole repository, 1,106 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, which holds the touched modules, gives the same 269 failing ids as round #191's run.
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,782 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `2f3a788`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Still not reviewed from the owner's merges since round #182:** #398, #416, #419, #447, #448, #450, #453, #456,
  #458, #461, #463, #465, #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 32 were run again with the new tests, and all 32 are killed.
