# Design and architecture review — the owner's #403

Date: 2026-11-13. Baseline: `e00bd41` (main after round #164's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 05:12 UTC firing on 2026-11-13. Main had not moved, so it takes one of the three audit merges
that earlier rounds left: **#403**, merged on 11-11 at 21:14 UTC. #403 adds a pinned import of local CT layers and
labels into the checkout's ink-training layout (`src/vesuvius_autoresearch/core/surface_volume_import.py`, with a
command in `scripts/training/prepare_surface_volume.py` and a guide), and retires two legacy figure generators.

## What changed

### Sixteen of the import's guards are now tested (`tests/test_surface_volume_import.py`)

This round made 33 mutants of the import module. #403's tests killed 14. Ten new test functions (20 cases) kill 16
of the 19 survivors. Each passes on the module as merged and fails with its mutant:

- **A layer rewritten at the same size is refused by its digest.** This is the guard the import is named for, and
  no test reached it. #403's test of a changed source appends bytes, so the byte count catches the change before
  the digest is compared. An uncompressed 16-bit TIFF has the same size whatever its values, so for a re-rendered
  layer the digest is the only check. With the digest comparison removed, #403's tests still passed and the import
  published the changed layer.
- **Alignment is declared with `True` and nothing else.** `1`, `"yes"` and `None` are refused.
- **The layer range is checked before any file is read**: more than 512 layers, an empty range, a negative start
  and a boolean start.
- **The pixel limit cannot be raised above the decoder's.**
- **A PNG under a layer's name is not a CT layer.**
- **The volume limit admits exactly the padded chunk storage** and refuses one byte less.
- **A source that changes during planning is refused**, both while it is captured and later, before the plan is
  returned.
- **Each manifest rule refuses its own edit**, by its own message: another contract number, a source range longer
  than the depth, a layer index out of order, a layer file whose name is not its index, a relative path, and a
  shortened digest. #403's test of edited manifests accepts any ValueError, so one rule could mask another.
- **A build budget below the manifest's geometry is refused** before any source is read.

The other three survivors are not worth a test:
- the decoded shape is checked against the manifest, but a mismatch would fail the array write anyway;
- the read-back comparison needs a faulty Zarr store to fail;
- a NaN in the manifest is refused by the field checks whether or not the JSON parser rejects it.

No code changed. I found no defect in the module.

## Verified, no change needed

- **The guide's limits are the module's.** `docs/TRAINING_DATA_IMPORT.md` gives 512 planes, 512 MiB a file, 1 GiB
  of padded chunk storage, a 2 MiB manifest, chunks up to 1 × 128 × 128, and names of at least two digits that keep
  all digits above 99. Each matches a constant or an expression in the code.
- **The build takes the tighter of the two budgets.** The effective limit is the smaller of the command's and the
  manifest's, for each of the three. #403's own test covers that, and its mutant fails it.
- **Labels and masks are copied as captured bytes**, and the CT digest is taken over the decoded layers in Z order.
  #403's tests cover both.
- **A failed build publishes nothing.** Each refusal above that reaches the build leaves no output directory.

## Observations for the owner (not changed)

- **One of #403's tests fails in a container without villa.**
  `test_training_dataset_accepts_prepared_ct_labels_and_mask` stops at a file missing under `villa/`. It is one of
  the 171 suite ids that fail here on main.
- **A mutation run stops at the first failing test.** Because of the test above, my first run of the 33 mutants
  reported all 33 as killed. I reran them with that test deselected. Earlier rounds' runs in this container were on
  modules whose tests all pass here, so they are not affected.

## Verification

- **The touched module.** `test_surface_volume_import.py` gives 60 passed and 1 failed, against 40 passed and the
  same 1 failed on `e00bd41`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 216 modules give the same 171 failing ids on `e00bd41` and on this branch.
- **The test modules outside the suite.** The 250 modules give the same 23 failing ids on `e00bd41` and on this
  branch.
- **The doc audit**, run alone, lists the same unresolved references as on `e00bd41`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The baseline figures for `e00bd41` are round #164's runs of its branch head, whose tree is identical.

## A note on this round's work

- **Only the import module was reviewed in depth.** Of the rest of #403, I checked the guide's limits against the
  code. I did not review the retired figure generators, the command-line wrapper or the changes to
  `fragment_conversion.py`.
- **Still not reviewed:** #396 and #404, and the estimator and resampler of #390.
- **The mutants are a sample** of the module's checks, not a sweep.
