# Design and architecture review — a big-endian uint16 volume read by inference and the unlabeled dataset

Date: 2026-10-21. Baseline: `37996c89` (main after #179).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `src/vesuvius_autoresearch/core/vesuvius_loader.py`, the loader's lines the standard suite does not run. In
the coverage run of #179 it was at 87%.

Among the lines missed were:
- `FastVesuviusVolume.read_ct`'s uint16 branch, never reached by any test;
- its unknown-dtype fallback, which divides by 255 with a warning.

Main has not moved since #179. There are no open pull requests. This round covers the 21:12 UTC firing.

## What changed

- **`read_ct` divided a big-endian uint16 volume by 255, not 65535.**
  - It chooses the scale by `ct.dtype == np.uint16`. A big-endian `>u2` array is not equal to `np.uint16`, nor to
    `np.uint8`, and is not floating. So it reached the unknown-dtype fallback, `/255`, with a rate-limited
    "unknown CT dtype" warning.
  - A big-endian voxel of 65535 reached the model as 257.0, where a little-endian one reaches it as 1.0. Measured
    on a zarr of each:

    | dtype | value | `read_ct` before | after |
    |---|---|---|---|
    | `uint8` | 255 | 1.0 | 1.0 |
    | `<u2` | 65535 | 1.0 | 1.0 |
    | `>u2` | 65535 | **257.0** | 1.0 |
    | `>f4` | 0.5 | 0.5 | 0.5 |

  - **Who reads through it:** `FastVesuviusVolume.__getitem__`. Its callers are:
    - `VesuviusS3Dataset`, the unlabeled volumes UA-MT trains its consistency on;
    - `scripts/inference/predict.py`, `ensemble_predict.py` and `scripts/production_predict.py`, whose CT preview
      also calls `read_ct` directly;
    - `scripts/verify_patch.py` and `scripts/build_volume_cartographer_readiness.py`, which only print or smoke-test.
  - **The labeled dataset was already right.** It reads through `get_raw_patch`, which converts a non-native byte
    order first ("e.g. a big-endian zarr; torch needs native").
    - Its test in `tests/test_labeled_dataset_contracts.py` could not show it.
    - The test built the dataset in its permissive mode, where a failed read becomes a zero patch with a warning, and
      asserted only an upper bound.
    - With the conversion removed, torch refuses the non-native array, the patch is zeros, and the test passed.
  - So training and validation scaled a big-endian volume by 65535, while inference and the unlabeled volumes
    scaled it by 255.
  - **Change:** `read_ct` converts a non-native byte order before choosing the scale, as `get_raw_patch` does.
  - **Today's exposure could not be checked here.**
    - The loop's `unlabeled_uris` and its benchmark are the local `PHercParis2Fr47` and `PHercParis2Fr143` zarrs,
      which this container does not have. Their source layers are uint16 TIFFs.
    - A zarr written from a native numpy array is little-endian.
    - But PIL reads a big-endian 16-bit TIFF as `>u2`, and zarr stores an array in the byte order it is given. So a
      zarr built by stacking big-endian TIFFs would be big-endian.
    - A rendered segment is written as uint8 TIFFs, so rendering does not carry the byte order on.
    - The loop deletes `run_result.json` before each run, so only the last run's `loader_warnings`, or its `run.log`,
      would show a `ct_unknown_dtype` warning from an affected volume. Worth a look on the owner's machine.
- **Tests** (in the standard suite):
  - `tests/test_vesuvius_s3_dataset.py`. `read_ct` and `FastVesuviusVolume[...]` are checked on zarrs of uint8,
    `<u2`, `>u2` (at 65535 and 4096) and `>f4`:
    - each returns float32 at the dtype's scale;
    - none raises the unknown-dtype warning.

    A `<i2` volume still falls back to `/255`, with the warning.
  - `tests/test_labeled_dataset_contracts.py`'s big-endian test now reads strictly, so a failed read raises, and
    requires a non-zero patch.
  - Each of these mutants fails them:
    - `read_ct`'s conversion removed (the two `>u2` cases fail on main's loader);
    - `get_raw_patch`'s conversion removed;
    - the unknown-dtype warning dropped.

## Verified, no change needed

- **`get_raw_patch`** already converts the byte order, then reads uint16 as int32 for torch. The labeled dataset's
  normalisation (`/255` for uint8, `/65535` for the int32 that was uint16, floats passed through) follows from it.
- **The labeled dataset's dtype check** reads the kind and item size (`kind == "u"`, `itemsize` 1 or 2, or
  `kind == "f"`), so it already accepts a big-endian uint16.
- **Comparisons with `np.uint8` elsewhere** are unaffected, since a one-byte type has no byte order.
- **Native dtypes are unchanged.** For uint8, uint16, float32, float64, int16 and bool the conversion is skipped, so
  the result is the same as before. A big-endian float gives the same values as before.
- **The read is always numpy.** Both the volume-cartographer wrapper's `get_chunk` and the loader's fallback return
  `np.asarray`, and the ridge channel gives the same result on a big-endian and a little-endian volume.

## Observations for the owner (not changed)

- **Two other scale choices compare with `np.uint16`** on TIFFs read through PIL, which keeps a big-endian 16-bit TIFF
  big-endian:
  - `repro/ink_segformer/dataset.py` (lines 24 and 42), whose denominator falls to 255;
  - `scripts/ink_depth_profile.py` (line 76), whose `>> 8` is skipped.

  Fragment surface volumes are normally little-endian TIFFs, and the first is a frozen reproduction, so neither is
  changed.
- **`scripts/dataset_inspection.py` (line 70) refuses a `>u2` volume.** It accepts only `np.dtype("uint8")` and
  `np.dtype("uint16")`, though the labeled dataset accepts a big-endian volume.
  - It is used by the scan and visualisation scripts.
  - It refuses loudly rather than mis-scaling, and it is not on the loop's, validation's or inference's path.
- **An unknown big-endian dtype's warning** now names the native type (`int16` for `>i2`).

## Verification

- `pytest tests/test_vesuvius_s3_dataset.py tests/test_labeled_dataset_contracts.py`: 45 passed, 6 of them new.
- Ruff 0.9.10 `check` and `format` are clean on both changed files, which were formatted before.
- **The standard suite with the locked packages** (as in #178): 2757 passed, 9 failed, 22 skipped and 1 xfailed. That
  is #179's 2752 plus the five new cases, on the first commit (`6e6555ee`), with the same nine villa-file failures.
  The later commit changes only the two test files above. The smoke test gave 9 of 11 passed and 2 skipped, as on main.
- **Independent review** of the first two commits, in a worktree without villa. It found nothing blocking.
  - It confirmed:
    - native dtypes are unchanged, and the converted values are bitwise equal;
    - the wrapper and ridge paths;
    - the callers and the labeled dataset's own conversion;
    - the uint8 renders and the warning counts in `run_result`;
    - the two observations on PIL-read TIFFs.
  - Its should-fix findings:
    - the S3 zero patch's depth: `VesuviusS3Dataset` clamps `num_layers` to the volume's depth, so its zero patch and
      its reads match, and the observation was wrong. It is removed.
    - the labeled dataset's big-endian test could not catch a lost conversion.
  - Its nits:
    - `dataset_inspection.py`'s refusal;
    - two more callers;
    - the exposure reasoning: a test parameter is no evidence of a real big-endian volume, and the TIFF-to-zarr path
      is;
    - `run_result.json` is deleted before each run;
    - an always-true assertion in the new test;
    - the untested fallback;
    - the warning's dtype name.

  All are addressed above.
