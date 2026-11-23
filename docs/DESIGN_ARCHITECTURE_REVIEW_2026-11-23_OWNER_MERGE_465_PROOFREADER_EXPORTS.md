# Design and architecture review — the owner's #465, verifying approved proofreader exports

Date: 2026-11-23. Baseline: `ecc3e30` (main after round #204's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 13:12 UTC firing on 2026-11-23. Main had not moved since round #204's merge.

It takes **#465**, which lets `scripts/check_proofreader_session.py --verify-approved-patches` check the TIFF pairs
Villa's pinned proofreader saves for each approved patch. `src/vesuvius_autoresearch/core/proofreader_session.py`:
- rebuilds the writer's approved list from the progress log, and refuses a duplicate approval or a list or count
  that differs from it;
- inventories `imagesTr` and `labelsTr`, refusing links, hard links, unlisted files, missing files and files over
  budget;
- reads each TIFF within the file budget, and requires one uncompressed, untiled, complete cube of the patch size;
- compares each image with the recorded CT voxel for voxel, keeps labels within 0..255, and refuses any change to
  the exports, the CT or the record while it reads them.

This module is not registered. #483, still to be reviewed, later added the edited-label comparison.

## What changed

### A TIFF that tifffile cannot parse is refused as the other malformed exports are

`_capture_tiff` let tifffile's own `TiffFileError` out when a saved TIFF's structure could not be parsed, as when
the file is cut through its last IFD. `TiffFileError` is not a `ValueError`. `check_proofreader_session.py` reports
`OSError`, `ValueError`, `TypeError`, `KeyError`, `RuntimeError` and `OverflowError` as "Proofreader session check
failed", so such a file ended the check with a traceback instead. It still exited non-zero, so nothing was
accepted. The parse is now wrapped, and the file is refused as "unreadable proofreader TIFF" with its path. The new
test of it fails on the old code.

### The export check is tested without the pinned proofreader (`tests/test_proofreader_session.py`)

#465's own tests reach the check only by launching Villa's pinned proofreader. That needs the Villa checkout, so 59
of the module's 69 tests fail here, and the portable CI profile does not include the module. Sixteen new test
functions, 29 cases, call `_verify_exports` directly. They use TIFF pairs written as the pinned writer writes them,
uncompressed and one page per slice, against an in-memory CT. They cover:
- **pairs equal to the CT** verified and hashed, a skipped entry left out, and no approvals with no folders giving
  zero pairs;
- **an image one voxel off, or of another dtype**, refused;
- **labels at −1 or 256** refused, and labels at 0 and 255 accepted;
- **the approved list.** A duplicate is refused, as are a wrong count, a count of `True`, a listed field that
  differs and a listed patch that is missing. A missing date is rebuilt as empty.
- **the folders.** An unlisted file, a missing file, a missing folder, a hard link, a linked folder and a linked
  file are each refused.
- **the budgets** on one file, on all bytes, on entries, and on a decoded CT chunk;
- **TIFFs the pinned writer would not write**: compressed, tiled (including one tile the size of the page), short,
  complex, and a float label;
- **a file cut short**, through its structure or through its last strip;
- **an export touched while it is read.**

### Two mutants are not killed

This round made 26 mutants of the check, and the new tests kill 24.
- **Moving the early entry check by one is equivalent.** The inventory counts the same folders and files after it
  and refuses the same number.
- **Accepting deflate as well as uncompressed strips is not killed.** A compressed strip is never as long as the raw
  one, so the strip-size check refuses it anyway. Only a crafted file whose compressed strips are padded to the raw
  length would tell the two apart.

## Verified, no change needed

- **The guide matches the check.** `docs/PROOFREADER_SESSION_RECORDS.md` says:
  - each TIFF must be a complete uncompressed cube with strip byte counts matching the page;
  - the image must match the CT crop voxel for voxel and keep its dtype;
  - labels must be integers or booleans in 0..255;
  - unlisted files are refused.

  All four hold in the new tests.
- **Changes during the check are caught.** The export folders are inventoried before and after the reads, and the
  progress file, the CT tree and the record are rehashed or re-inventoried after them.

## Observations for the owner (not changed)

- **The export check runs in CI only if its module does.** The portable profile does not list
  `tests/test_proofreader_session.py`, whose other tests need Villa's proofreader. The new tests need only NumPy and
  tifffile. A Villa-free module of them listed in the portable profile would run the check on every push.

## Verification

- **The touched module.** `test_proofreader_session.py` gives 39 passed, against 10 before: the 29 new cases pass.
  Its other 59 fail here as before, all among the standard suite's villa ids, because they launch Villa's pinned
  proofreader.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on both
    changed files.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules including the touched one, gives the same 278 failing ids as round #204's
  run. It ran with the fix and the new cases.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #204's run, and the same 3,253
  passed. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `ecc3e30`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **The fix is in unregistered code**, with a test that fails before it.
- **Still not reviewed from the owner's merges since round #182:** #468 to #478, #480, #483, #485, #488, #489, #493
  and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 26 were run again with the new tests: 24 are killed, one is equivalent, and one
  needs a crafted file.
