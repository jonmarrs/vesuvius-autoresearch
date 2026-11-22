# Design and architecture review — the owner's #466, the explicit patch catalog

Date: 2026-11-22. Baseline: `45cc67f` (main after round #184's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 16:12 UTC firing on 2026-11-22. Main had moved once since round #184 began, with the owner's
#483. Round #184's PR was merged after main was merged into it.

It takes **#466**, merged on 2026-11-17. #466 moves the reading of an explicit `patches.json` into
`read_patch_catalog` in `src/vesuvius_autoresearch/core/patch_catalog.py`. The reader:
- captures the file under a 16 MiB cap;
- refuses duplicate JSON keys;
- checks that `patch_size` and `num_patches` match, when present;
- refuses an origin whose patch would not fit the volume's YX grid;
- returns the origins in order with the SHA-256 of the exact bytes it parsed.

The labeled dataset now uses it for training and validation, and validation's input fingerprint compares that hash
with the file's.

## What changed

### Seven guards of the catalog reader are now tested (`tests/test_labeled_dataset_contracts.py`)

This round made 22 mutants of `read_patch_catalog` and its capture cap. The existing tests of six modules that build
datasets from catalogs killed 15. Two new test functions, 10 cases, kill the other seven. They call the reader
directly, so they run without villa:
- **The patch size must be a positive integer.** A fractional, boolean, zero or string size is refused. A NumPy
  integer is taken, with an origin at the grid's far edge.
- **A catalog of the wrong form is refused:**
  - a `patches` value that is a dict or a string;
  - a `patch_size` of `16.0` or a `num_patches` of `true`, each equal in Python to the right value;
  - a negative origin;
  - nesting too deep to parse, which is reported as an invalid catalog rather than a `RecursionError`.

No code changed. No defect was found.

### Why these survived

Most of the loader's dataset tests need villa's patch finder, and 80 of the six modules' tests fail here for that
reason. The catalog tests that do run pass a valid patch size and well-formed lists, so the reader's checks of a bad
size, a non-list `patches` and a negative origin were never reached.

## Verified, no change needed

- **A missing or dangling catalog does not fall back to discovery.** The dataset now treats any given
  `patches_json` as explicit. Both training call sites pass it only when `os.path.lexists` finds it, so a dangling
  link is refused by the capture, not skipped. #466's test covers an explicit missing path.
- **Validation hashes the catalog through the same capture.** `promotion.py` hashes `capture_patch_catalog`'s
  bytes, and the dataset returns the hash of the bytes it parsed. A catalog rewritten during construction and
  restored fails the comparison. #466's test covers that.
- **The documentation matches the code.** `docs/TRAINING_DATA_IMPORT.md` says:
  - catalogs are accepted up to 16 MiB;
  - the `patches` list must be nonempty, with integer origins whose full patch fits;
  - `patch_size` and `num_patches` must match when present;
  - order and repeated origins are kept.

  All four hold.

## Observations for the owner (not changed)

- **Repeated origins are kept on purpose.** The guide and #466's test both say so. A catalog that lists one origin
  many times weights the sampler towards it, and nothing reports how many origins are distinct.
- **Keys other than `patches`, `patch_size` and `num_patches` are ignored**, in the catalog and in each entry. A
  misspelt `patch_sizes` passes without notice.

## Verification

- **The touched module.** `test_labeled_dataset_contracts.py` gives 46 passed and 19 failed, against 36 and 19 on
  `45cc67f`. The 19 need villa.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,091 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** 265 failing ids. The differences from round #184's 251 are all in
  `test_proofreader_session.py`, which #483 rewrote: 15 new ids and one renamed away. Each failure in that module stops
  with "Villa proofreader missing".
- **The test modules outside the suite.** The same 264 modules give the same 23 failing ids, and 2,744 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `45cc67f`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`train.py` and `promotion.py` are in `scripts/training/`**, where only tests may be added. Their #466 changes
  were read, not mutated.
- **Still not reviewed from the owner's merges since round #182:** #447, #448, #450, #453, #456, #458, #461 to #463,
  #465, #468 to #478, #480 and #483.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 22 were run again with the new tests, and all 22 are killed.
