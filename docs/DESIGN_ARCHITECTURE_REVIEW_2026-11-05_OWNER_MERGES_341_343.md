# Design and architecture review — the owner's #341 and #343

Date: 2026-11-05. Baseline: `85fd9e87` (main after #343).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 06:12 UTC firing.
- **#341 fixes tiled fiber filtering at singleton boundary tiles.** It merged during round #147's validation and was
  left for this round.
  - At a physical face, two composed second-order one-sided gradients reach three smoothed voxels inward. A tile
    holding only the face voxel, at the accepted minimum halo, had one source plane too few.
  - `_block_bounds` now extends face windows to the Gaussian support plus four. It is used by `_detect_tiled`,
    `fiber_direction_tiled` and `streaming.blocks`.
  - A CPU replay on a public CT crop and 43 new tests come with it.
- **#343 validates each walk destination before recording it** (`trace._walk`).
  - A destination whose orientation is masked, zero or nonfinite now stops the walk with `invalid_direction` before
    its point is recorded or claimed.
  - `WALK_VERSION = 2` goes into the trace JSON's `tracing_recipe`.

This round changes no library code. It does three things:
- adds a test of #341's report against its receipt;
- makes one of #343's tests type-check;
- records one observation on #343.

The owner's #344 (detector output preflight) merged at 06:15 UTC, after this firing. It touches none of this
round's files, and the next round reviews it.

## What changed

- **#341's report and doc had no test** (`tests/test_fiber_boundary_halo_record.py`, listed in the suite).
  - The new module binds `reports/fiber_boundary_halo_2026-11-05.md`'s table, inputs and parameters to the receipt
    (`reports/evidence/fiber_boundary_halo_2026-11-05.json`).
  - It checks `_block_bounds` against the report's and the doc's two claims:
    - singleton face tiles get the support plus four;
    - every window keeps the `block_size + 2 * halo` bound.
  - Eight mutants fail it:
    - the table's counts and error;
    - the parameters;
    - the fixture hash;
    - a face support of plus three or plus twenty-four;
    - the end-face extension removed.

- **#343 left mypy failing** (`tests/test_fiber_trace.py`).
  - `_invalid_destination` builds `plane = [slice(None)] * 3` and then sets one entry to an integer. Mypy reads the
    list as `list[slice]` and rejects the assignment.
  - This is the only error over the whole repository, so main has not been mypy-clean since #343.
  - The list is now annotated `list[slice | int]`. The 41 tests in the module still pass.

## Verified, no change needed

- **#341's windows are exact.**
  - **The reach.** The Hessian smooths with `gauss_sigma` (support `int(4σ + 0.5)`), then takes `np.gradient` twice
    with `edge_order=2`. At a face the second pass reaches the fourth voxel in, three beyond the face voxel.
    - A singleton core at the far face, with the minimum halo of support + 2, therefore misses one plane.
    - Two-voxel cores do not. So the defect is singleton-only, as the report says.
    - The support + 4 window is exactly enough.
  - **Random volumes.** In 180 comparisons, tiled ridges, vesselness and orientation equal the dense path exactly.
    The volumes were random shapes at the minimum halo, with blocks of 1–8 and σ of 0, 1 and 2.
  - **The 43 new tests.** All pass on the fix. With the old `detection.py` and `streaming.py` swapped into `src/`,
    all 43 fail on value mismatches, as #341 says.
    - `PYTHONPATH` cannot do this swap: `pyproject.toml` puts `src` first on pytest's path.
  - **The receipt.** It names the baseline `detection.py` at `71045374`. Its candidate hashes are `detection.py` and
    `streaming.py` on main. Its comparisons match the report's table.
- **#343's destination check.**
  - **What it does.** The check runs after the bounds, collision and response gates, so their stop reasons keep
    precedence. It uses the same nearest-voxel lookup as the next step's direction. So the loop-top
    `invalid_direction` can now fire only at the seed.
  - **Its tests.**
    - Removing the check fails 18 tests in `test_fiber_trace.py`.
    - Dropping the new `isfinite` guard fails 4.
  - **Nonfinite directions.** A nonfinite seed direction now returns `None` and the seed is skipped. In seed NMS, a
    nonfinite tangent skips the disc stamp, as the old NaN tangent's empty disc did.
  - **What it changes.**
    - The `trace` command records `walk_version` with each run.
    - The relink fixes reviewed in round #147 are unaffected.

## Observations for the owner (not changed)

- **The floors refresh can carry a walk-1 tracer row into a current report.**
  - `floors --all-cubes` keeps a prior report's `tracer_strict_relink` row whenever the measurement provenance
    matches. That provenance is the data, scoring version, parser, tolerance and mask threshold. It does not
    include the walk version.
  - Nothing else writes that row: `trace` writes its own per-cube JSON, which now records `walk_version`.
  - So every existing all-cubes report's tracer row is walk 1. A floors refresh would keep it beside fresh floors,
    with nothing marking it as walk 1.
  - #343's doc says past tracing scores "need a fresh run before they can describe current code".
  - A remedy would change your workflow: drop the carried row unless its report records `walk_version == 2`, or
    record the walk version beside it. It is left to you.
- **`docs/FIBER_DETECTION.md` still says tiled-vs-dense parity "holds to 1e-4".** With #341 it is exact at the
  accepted halos on CPU. The figure is the June GPU report's, so it stays as written.

## Verification

- **The touched modules**, `test_fiber_boundary_halo_record`, `test_fiber_direction_tiled`,
  `test_fiber_streaming_cli` and `test_fiber_trace`, pass.
- **Ruff and mypy.** Ruff 0.9.10 `check` and `format` are clean on the changed files. Mypy is clean over the whole
  repository: 888 files, after the fix above.
- **The standard suite** gives round #147's 70 failing ids:
  - the 43 standing failures;
  - the 25 SDK cases;
  - the 2 collection errors.
- **The 240 test modules outside the suite** give 2,255 passed, 82 skipped, 13 failed and 21 errors.
  - The failing ids are round #147's.
  - The 3 extra passes are #340's `test_gpu_window_2026_11_03_record.py`.
- **The doc audit**, run alone, adds three unresolved references.
  - All three are round #147's record quoting commits of other repositories: villa `9c343a1` and `baf5e605b`,
    and ScrollGT `1605fadb`.
  - This record adds none.
