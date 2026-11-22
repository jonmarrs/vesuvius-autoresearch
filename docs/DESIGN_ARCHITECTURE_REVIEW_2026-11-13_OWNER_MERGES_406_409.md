# Design and architecture review — the owner's #406, #407 and #409

Date: 2026-11-13. Baseline: `65639e8` (main after #409).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the hourly firings from 00:12 to 03:12 UTC on 2026-11-13. It takes the three sampler fixes the
owner merged on 11-12 (times in UTC):
- **#406** (03:07) reads the last in-volume voxel in `sample_volume_trilinear`, in `repro/sota_data/canvas_shift.py`.
- **#407** (05:07) reads the last in-plane cell in `sample_tifxyz`, in the same module, and stops the probe's tifxyz
  reader at the end of the file.
- **#409** (23:27) ignores a zero-weight NaN in the fiber tracer's `_trilinear`, in
  `src/vesuvius_autoresearch/fibers/trace.py`.

All three apply one rule: a neighbour whose interpolation weight is zero is not read, so a point exactly on the far
face is that voxel or cell and not NaN.

Not covered: the rest of #390's module, and #396, #403 and #404. The last section says why. #401 arrived during the
round and is left to the next one.

## What changed

### #407: an empty crop samples as no surface, not a traceback (`repro/sota_data/canvas_shift.py`)

Since #407 the probe's tifxyz reader stops at the file, so a window wholly past the file comes back as an empty crop.
The probe's `_surface` passes that crop to `sample_tifxyz`, which raised IndexError ("index -1 is out of bounds for
axis 0 with size 0"). Before #407 the reader returned a crop of NaN and the window read as no surface.

`sample_tifxyz` now returns NaN for every sample when a plane has no rows or no columns. Two new tests fail on the
merged code: one on empty planes, and one that reads past a real TIFF and samples the result.

Whether the probe ever asks for such a window depends on the canvases, and I did not establish that.

### #406: a point that is not a voxel index is not cast to one (`repro/sota_data/canvas_shift.py`)

`sample_volume_trilinear` cast every coordinate to an integer before it masked the non-finite ones. NumPy warns on
that cast ("invalid value encountered in cast"), and what it yields for a NaN is not defined. The result was still
NaN, because the mask came afterwards. #407 fixed the same thing in `sample_tifxyz`, with the comment "Floor of a
non-finite coordinate warns and is not a cell index".

The probe passes every tifxyz sample to this function, holes included, so any surface with a hole reaches that
cast. The function now replaces a non-finite coordinate, or one too large for an index (2^62 or more), before the
cast. Those points are NaN, as before. The new test turns warnings into errors and fails on the merged code.

### Eleven guards no test reached

- **#409's sampler** (`tests/test_fiber_trace.py`). Of 13 mutants, #409's tests killed 8. Three new tests kill the
  other five and one variant:
  - a negative index on any axis is out of bounds and does not wrap to the far face;
  - the snap onto a face is 1e-9 wide, so a point 1e-6 outside is out of bounds;
  - an infinite voxel with positive weight gives NaN, and none at weight zero;
  - the nearest voxel of a point that is outside, non-finite or not three numbers is None.
- **#406's and #407's samplers** (`tests/test_canvas_shift.py`). Of 16 mutants, the owner's tests killed 10. New
  tests kill the other six:
  - a NaN voxel beside an exact voxel is not read;
  - a −1, an infinity or a NaN in the y or x plane alone is a hole;
  - a hole inside the plane counts even at weight zero, as #407's docstring says;
  - only z must be positive: a y of 0 is a coordinate;
  - the reader's empty crop past the file.

Each new test passes on the code and fails with its mutant (15 of 15, counting the reverted fixes).

## Verified, no change needed

- **The three samplers give the same values as before wherever the old ones gave a value.** I ran each against its
  version before the fix on random points that include exact voxels and the far faces:
  - the tracer's `_trilinear`: 4,000 points, identical;
  - `sample_volume_trilinear` at levels 0 and 2: identical where both are finite. The old one gave NaN at 380
    points on a far face; the new one gives a value at all of them;
  - `sample_tifxyz` on a plane with a hole: 5,002 valid samples before and 5,146 now. None was lost, the largest
    difference is 3e-15, and every gained sample is on the last row or column.
- **#409 changes no trace through an infinite voxel.** `_trilinear` now returns NaN there instead of infinity, and
  the walk stops on any non-finite response.
- **#407's weights match its corners**, in the order the code lists them, and a needed corner outside the plane
  still makes the sample NaN.
- **The reader keeps a leading NaN row for a negative start**, so index 0 is still the requested row. Only the part
  past the file is dropped.

## Observations for the owner (not changed)

- **The two rules for a zero-weight neighbour differ.** `sample_tifxyz` counts a hole inside the plane at weight
  zero; the two trilinear samplers ignore a NaN voxel at weight zero. #407 documents its choice. The effect is that
  a sample exactly on a cell whose next cell is a hole is NaN.
- **The probe's `_volume_at` still casts a non-finite coordinate** before it masks it. Its result is unaffected. It
  fetches chunks, so a test of it needs more scaffolding than this round had.
- **`_nearest_index` rounds a half to the even voxel** (0.5 to 0, 1.5 to 2), as Python's `round` does. #409 kept
  this.
- **#401 changes what the roadmap says about November.** #401 reports the First Letters kill test. The prize roadmap
  merged in #410 was written before it and still lists the kill test as waiting.

## Verification

- **The touched modules pass.** `test_fiber_trace.py`, `test_canvas_shift.py` and `test_canvas_artifact_contracts.py`
  give 138 passed, against 130 on `65639e8`: eight new test functions.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    three changed Python files.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 216 modules give the same 171 failing ids on `65639e8` and on this branch.
- **The test modules outside the suite.** The 249 modules give the same 23 failing ids on `65639e8` and on this
  branch.
- **The doc audit**, run alone, lists the same unresolved references on `65639e8` and on this branch.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The failing ids are this container's, as in the last round: it has no villa checkout.

## A note on this round's work

- **The usage limit interrupted the round once**, between the mutant runs.
- **#390's estimator and resampler were not reviewed.** This round read the two samplers that #406 and #407 changed,
  not `fit_shift`, `measure_shift` or the resampling onto the tifxyz grid.
- **#396, #403 and #404 are still not reviewed.** They are repository-wide audits (#396 alone touches about 90
  files). At the depth this session can afford they need a round to themselves.
- **#401 arrived at 03:40 UTC**, during the round. It is not in this branch.
- **The mutants here are a sample**, chosen from the lines the three PRs changed, not a sweep of the modules.
