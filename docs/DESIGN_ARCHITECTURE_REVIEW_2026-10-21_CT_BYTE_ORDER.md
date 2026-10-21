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
    - `scripts/inference/predict.py`, `ensemble_predict.py` and `scripts/production_predict.py`.
  - **The labeled dataset was already right.** It reads through `get_raw_patch`, which converts a non-native byte
    order first ("e.g. a big-endian zarr; torch needs native"). `tests/test_labeled_dataset_contracts.py` tests a
    `>u2` volume there.
  - So training and validation scaled a big-endian volume by 65535, while inference and the unlabeled volumes
    scaled it by 255.
  - **Change:** `read_ct` converts a non-native byte order before choosing the scale, as `get_raw_patch` does.
  - **Today's exposure could not be checked here.**
    - The loop's `unlabeled_uris` and its benchmark are the local `PHercParis2Fr47` and `PHercParis2Fr143` zarrs,
      which this container does not have. Their source layers are uint16 TIFFs.
    - A zarr written from a native numpy array is little-endian, and read correctly.
    - `tests/test_surface_render_contracts.py` tests a `>u2` source, so such scroll volumes exist. A rendered segment
      is written as uint8 TIFFs, so rendering does not carry the byte order on.
    - On the owner's machine, the loop's `run_result` counts would show a `ct_unknown_dtype` warning if any volume
      it reads were affected.
- **Test** (`tests/test_vesuvius_s3_dataset.py`, in the standard suite). `read_ct` and `FastVesuviusVolume[...]` are
  checked on zarrs of uint8, `<u2`, `>u2` (at 65535 and 4096) and `>f4`:
  - each returns native float32 at the dtype's scale;
  - none raises the unknown-dtype warning.

  On main's loader the two `>u2` cases fail.

## Verified, no change needed

- **`get_raw_patch`** already converts the byte order, then reads uint16 as int32 for torch. The labeled dataset's
  normalisation (`/255` for uint8, `/65535` for the int32 that was uint16, floats passed through) follows from it.
- **The labeled dataset's dtype check** reads the kind and item size (`kind == "u"`, `itemsize` 1 or 2, or
  `kind == "f"`), so it already accepts a big-endian uint16.
- **Comparisons with `np.uint8` elsewhere** are unaffected, since a one-byte type has no byte order.

## Observations for the owner (not changed)

- **Two other scale choices compare with `np.uint16`** on TIFFs read through PIL, which keeps a big-endian 16-bit TIFF
  big-endian:
  - `repro/ink_segformer/dataset.py` (lines 24 and 42), whose denominator falls to 255;
  - `scripts/ink_depth_profile.py` (line 76), whose `>> 8` is skipped.

  Fragment surface volumes are normally little-endian TIFFs, and the first is a frozen reproduction, so neither is
  changed.
- **The S3 dataset's zero patch on a failed read** has `num_layers` slices. A read from a volume shallower than
  `num_layers` has fewer, so a batch mixing the two would not collate. The read is rate-limited, counted and reported
  in `run_result`; volumes that shallow are not in the loop's data.

## Verification

- `pytest tests/test_vesuvius_s3_dataset.py`: 10 passed, 5 of them new. On main's loader the two `>u2` cases fail.
- Ruff 0.9.10 `check` and `format` are clean on both changed files, which were formatted before.
- **The standard suite with the locked packages** (as in #178): 2757 passed, 9 failed, 22 skipped and 1 xfailed. That
  is #179's 2752 plus the five new cases, with the same nine villa-file failures. The smoke test gave 9 of 11 passed
  and 2 skipped, as on main.
