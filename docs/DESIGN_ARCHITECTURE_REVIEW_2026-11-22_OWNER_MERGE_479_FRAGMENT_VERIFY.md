# Design and architecture review — the owner's #479, verifying a prepared fragment

Date: 2026-11-22. Baseline: `ac1bff6` (main after round #182's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 14:12 UTC firing on 2026-11-22. The session was down from 04:35 UTC on 2026-11-17 until
14:14 UTC on 2026-11-22. The 129 hourly firings in that gap were not run one by one. Round #182's PR was merged
first, after main was merged into it. Main had moved 124 commits, with 24 of the owner's merges, #447 to #480.

This round takes one of them: **#479**, which adds `verify` to `scripts/training/prepare_surface_volume.py`. The
work is in `verify_import` and two helpers of `src/vesuvius_autoresearch/core/surface_volume_import.py`. It
checks a prepared fragment against the `import.json` receipt that `build` saved, after the source TIFFs are gone.
Round #165 reviewed the importer's build path, from #403.

## What changed

### Twenty-three guards of the verifier are now tested (`tests/test_surface_volume_import.py`)

This round made 40 mutants of `verify_import`, `_recorded_source_path` and `_verified_json`. The module's existing tests
killed 14, and three cannot be killed (below). Eleven new test functions, 21 cases, kill the other 23:
- **The report names what was checked**: the shape, the chunk count, the receipt's own hash and the two PNGs'
  hashes.
- **A receipt of another contract or hash form is refused**: contract 2, a boolean contract, another CT hash
  encoding, a digest that is not a string, and an upper-case digest.
- **The receipt's own limits hold.** A limits record with an extra or a missing key is refused, and so is one above
  the decoder's pixel cap. A saved build budget or a manifest budget below the fragment's storage is refused even
  when the caller asks for more.
- **The budgets admit exactly the fragment's geometry**: 80 pixels and 480 bytes pass, 79 pixels does not.
- **The receipt's chunk byte count must be the geometry's**, as an integer: 481 and 480.0 are refused.
- **A store written with `/` separators is refused**, although its `.zarray` is otherwise the importer's.
- **The CT store must itself be a directory.** A symlink to the moved store and a plain file in its place are both
  refused, with the store's own message.
- **A fragment built with no mask verifies with only the label hashed**, and a dangling `mask.png` link in it is
  refused.
- **A label changed at the same size is refused by its digest.** The byte count alone would not catch it.
- **A label of another shape is refused even when the receipt records its digest.**
- **The receipt must be a finite JSON object**: a `NaN` in a field the verifier does not otherwise read, and a JSON
  array, are both refused.

No code changed. No defect was found.

### Three mutants no test can kill

- **Trying only Windows syntax for a foreign path.** On a POSIX host a POSIX path is already absolute as a local
  path, so the loop is reached only for Windows paths. The mutant would matter on a Windows host.
- **Comparing only the SHA-256 of a PNG.** Equal digests imply equal bytes.
- **Dropping the final symlink check.** To leave a symlink whose target has the recorded state, the original file
  must be moved, and a move changes its ctime on the filesystems here. The state check sees it first.

## Verified, no change needed

- **Only `verify` accepts foreign path syntax.** A Windows-recorded receipt verifies on Linux, and the same plan is
  still refused by `build` (#479's test). Layer names are read with the recorded path's own syntax.
- **Fragments built before #479 verify.** Zarr 2.18.3 writes all-zero chunks by default and leaves out
  `dimension_separator` when none is given; `verify` reads an absent separator as `.`. #479's test covers the
  missing key. Checked here: a store written that way holds every chunk, all-zero ones included.
- **The documentation matches the code.** `docs/COMMANDS.md` counts 28 commands, and the inventory has 28.
  `docs/TRAINING_DATA_IMPORT.md` gives an 8 MiB cap for the receipt and each Zarr header (`RECEIPT_BYTES`), the
  smallest of three limits for each budget, and exit 2 with a diagnostic on failure. All three hold.
- **The command turns the verifier's refusals into exit 2.** The refusals are `ValueError`s, and a missing file
  raises `OSError`. `ARTIFACT_ERRORS` catches both, as well as `TypeError` and `KeyError`.

## Observations for the owner (not changed)

- **`verify` shows that a fragment matches its receipt, not that the receipt is the original.** A receipt edited
  together with the data verifies. The report's `import_receipt_sha256` is what a caller would need to pin.
- **Files the importer did not write are not looked at.** A stray chunk outside the geometry, or any other file
  in the store, passes; Zarr ignores both when reading.
- **A hard-linked copy is refused.** Each file must have one link, so a fragment copied with `cp -al` or a
  hard-linking backup fails although its bytes are right. The guide says to copy the store and receipt; it does not
  say a hard-linked copy will not do.
- **The guide says `verify` prints `status: verified`.** It prints a JSON object whose `status` is `verified`, with
  the path and shape as well as the hashes and count the guide lists.

## Verification

- **The touched module.** `test_surface_volume_import.py` gives 93 passed and 1 failed, against 72 and 1 on
  `ac1bff6`. The failure needs villa's dataset code.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,091 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The same 249 failing ids as round #182's run on the merged tree, whose tree is
  `ac1bff6`'s. The 15 more than round #182's record lists are tests #465 added to
  `test_proofreader_session.py`; each stops with "Villa proofreader missing".
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,744 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `ac1bff6`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Only the verifier was mutated.** #479's build-side changes, `write_empty_chunks=True`, the explicit `.`
  separator and `_ct_attrs`, are bound by its existing tests and this round's report test, not by mutants.
- **Still not reviewed from the owner's merges since round #182:** #447, #448, #450, #453, #456, #458, #461 to #463,
  #465, #466, #468 to #478 and #480.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the verifier. All 40 were run again with the new tests: 37 are killed and the three
  above survive.
