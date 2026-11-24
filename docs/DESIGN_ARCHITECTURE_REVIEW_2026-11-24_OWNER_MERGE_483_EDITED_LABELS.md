# Design and architecture review — the owner's #483, approved labels against the edited Zarr

Date: 2026-11-24. Baseline: `08e9c4c` (main after round #222's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 07:12 UTC firing on 2026-11-24. Main had not moved since round #222's merge.

It takes **#483**, which adds `--verify-edited-labels` to `scripts/check_proofreader_session.py`. Villa's proofreader
can save an approved patch's TIFF pair and log the approval even when its write to `edited_labels.zarr` fails. The new
check compares every approved label TIFF, voxel for voxel, with the edited Zarr's crop at the logged ZYX origin.
`src/vesuvius_autoresearch/core/proofreader_session.py`:
- opens the edited Zarr read-only, after checking that it is a bounded, bare uint8 Zarr v2 array of the CT's shape,
  with zero fill and positive 3D chunks;
- compares the crops, and checks the store again afterwards for changes;
- adds what it compared to the report and the scope.

`verify_record` now also checks the source labels, not only the CT, for changes during the export reads.

This code is not registered material, so this round fixes the one defect it found.

## What changed

### Unreadable edited-label metadata is refused with the checker's own error (`proofreader_session.py`)

`_open_edited_labels` turned zarr's `MetadataError` into "invalid edited-label Zarr metadata", which covers a
`.zarray` without a required key. It did not cover a `.zarray` that is not JSON, or not a JSON object, as an
interrupted write can leave:
- `[]` or `null` made zarr raise `AttributeError`. The checker's command line catches `OSError`, `ValueError`,
  `TypeError`, `KeyError`, `RuntimeError` and `OverflowError`, not `AttributeError`, so it ended in a traceback.
  It still exited 1.
- Text that is not JSON gave the parser's message, such as "Expecting property name enclosed in double quotes",
  without the store's path.

Now any `ValueError`, `TypeError`, `KeyError` or `AttributeError` that zarr raises while opening the store is refused
as "invalid edited-label Zarr metadata", with the store's path, as a `MetadataError` already was. A test of four
unreadable `.zarray` files fails on the old code for three of them, and passes now.

### The edited-label check is tested without Villa (`tests/test_proofreader_session.py`)

#483's edited-label tests all run the pinned writer from Villa's proofreader source. Without a Villa checkout, as in
this container and in CI's `portable` job, none of them runs, and nothing tested the new code.
This round made 23 mutants of it, and the 39 tests of the module that run here killed none.

Nine new test functions, 25 cases with the four above, kill 22. The last is equivalent, below. They call
`_verify_exports` directly, as the module's other Villa-free tests do. They also call `verify_record` on a session
written by `create_record` with a stand-in proofreader file, whose progress log is written by hand.
- **The crops.** Labels equal to the store's crops are reported with the store's name, shape, dtype and count. A
  voxel that differs, or the crop stored at its Z and X swapped, is refused at the logged coordinates.
- **The store**, refused before any crop is read when it:
  - is missing, linked, or a group;
  - has metadata without chunks, the wrong shape, dtype or fill, or chunks of the wrong rank or of size 0;
  - has a decoded chunk over the file limit, or more files than the entry limit.

  A chunk exactly at the file limit is read.
- **A log with no approvals** still needs a compatible store, and reports zero crops, as the guide says.
- **A store that changes while its crops are read** is refused.
- **`verify_record`.**
  - The edited-label check alone also checks the TIFF pairs, and adds its sentence to the scope; the pair check
    alone does neither.
  - A CT or label source that changes during the reads is named as the one that changed.

## Verified, no change needed

- **The check reads the store the receipt names.** `verify_record` takes `output_label_zarr` from the recorded
  config, which must equal `recorded_config`'s: `edited_labels.zarr` in the resolved session folder.
- **The limits.** The store's files count against the effective limits on their own, as the guide says. A decoded
  uint8 chunk is its element count, so `math.prod(chunks)` against `max_file_bytes` bounds it.
- **A sparse store reads as zero.** #483's fixture gives the pinned writer a store opened with
  `write_empty_chunks=False`, and the guide says an all-zero approved crop can use the zero fill. A crop with no chunk
  files reads as 0, which the required zero fill makes the right value.

### One mutant is equivalent

**Reporting `len(approved) and len(pairs)` crops** changes nothing. The loop adds one pair for each approved patch,
or refuses, so the two counts are equal whenever the report is written.

## Observations for the owner (not changed)

- **`REPOSITORY_AUDIT.md`'s 2026-11-22 section** says the checker now reports unreadable metadata, and that the
  command line returned 1 for three malformed fixtures. That held for metadata without a required key. A `.zarray`
  of `[]` or `null` also returned 1, but through a traceback; this round's fix covers it. The section is the owner's
  dated record, so it is left as written.

## Verification

- **The touched module.** `test_proofreader_session.py` gives 64 passed here, against 39 before. The other 59 need
  Villa's pinned source, as before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the two
    touched files.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #222's run. It runs the touched module.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #222's run, with 3,449 passed and
  4 xfailed. One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `08e9c4c`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **The fix is one `except` clause.** The checks before and after it, and the messages of every other refusal, are
  unchanged. A `.zarray` naming a codec that is not installed now reads "invalid edited-label Zarr metadata" too,
  where it gave numcodecs' own message.
- **The tests write only under `tmp_path`.** The stand-in proofreader file is a text file that only fixes the hash
  the receipt binds.
- **Still not reviewed from the owner's merges since round #182:** #485, #488, #489, #493, #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 23 were run again with the new tests and the fix: 22 are killed, and the
  equivalent one is not.
