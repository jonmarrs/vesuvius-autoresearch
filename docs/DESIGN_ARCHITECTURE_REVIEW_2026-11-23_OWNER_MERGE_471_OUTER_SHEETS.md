# Design and architecture review — the owner's #471, the outer-sheet check

Date: 2026-11-23. Baseline: `0f7adfb` (main after round #209's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 18:12 UTC firing on 2026-11-23. Main had not moved since round #209's merge.

It takes part of **#471**, finding 126: PHerc. 0358's band, fitted and read by Studio. This round takes
`repro/first_letters/eligible_band/outer_sheets.py`, which the report's fourth limit quotes. At the band's middle
slice it casts 360 rays from the scroll axis through the surface prediction's distance field. For each fitted
winding it gives the median number of predicted-sheet runs beyond the winding along its rays, and how far the
outermost sheet lies from it. The report uses it to say that at that slice the fit reaches the edge of the predicted
sheet on most of w129's rays.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### The check is tested (`tests/test_first_letters_0358_band.py`)

`outer_sheets.py` had no tests of its own. Only the report test read the numbers it gave, so all 20 of this round's
mutants of it survived. Three new test functions kill all 20. They run the script on a small distance field with
two full rings of sheet, an arc of sheet over a sixth of the angles further out, and no data beyond.
- **The axis is sorted by z whatever order its points are listed in, interpolated in x and y, and halved to grid
  cells.** The test's axis is tilted, listed out of z order, and has different x and y.
- **Rays stay inside the slice**, and sheet and data cells leave out the cells with no value.
- **The outermost sheet is the last on each ray**, and rays that cross no sheet are left out of its median and of
  each winding's gap.
- **A winding is read within 3 voxels of the slice**, in grid cells, and binned by its own angle round the axis. One
  with no node near the slice gives `None`.
- **Runs are counted from 4 cells beyond the winding.** A winding on a sheet does not count its own, and a run that
  the counting starts inside counts once.
- **The gap is in working voxels**, and the runs are summarised by their median and their 10th and 90th
  percentiles.

No code changed. No defect was found.

## Verified, no change needed

- **The report quotes the record.** `reports/first_letters_0358_outer_sheets.json` gives:
  - for w129, an outermost sheet a median −2.1 voxels from the winding, a median of 0 runs beyond it and a 90th
    percentile of 8;
  - for w110, a median of 18 runs.

  The report's fourth limit says the same, and #471's report test checks it.
- **The rays and the windings use the same frame.** Columns are x and rows are y, both for the rays and for the
  windings' angles. A test whose axis has different x and y and whose winding covers only 60 degrees confirms it.

## Observations for the owner (not changed)

- **The script fixes the distance field's encoding instead of reading it.**
  - It takes a grid cell as 2 working voxels, sheet as stored values 1 to 127, and 0 as no data.
  - `band_fit_quality.DistanceField` reads the offset, unit and scale from the store's attributes, and counts a
    distance of 0 as inside the sheet.
  - A field written at another scale or offset would give wrong numbers here without an error. If the offset is
    128, a cell stored at exactly 128 is on the sheet for the fit's score and off it here.
- **The outermost data radius counts rays with no data as −1.** The outermost sheet radius leaves such rays out.
  The record gives the data radius, 2,671 voxels, but the report does not quote it.
- **The record wraps the script's output by hand.** The script prints to standard output. The record's `finding`,
  `described`, `script` and `arm` keys were added around that output, so re-running the script reproduces the
  numbers but not the record.

## Verification

- **The touched module.** `test_first_letters_0358_band.py` gives 11 passed, against 8 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,109 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #209's run.
- **The 309 test modules outside the suite** give the same 24 failing ids as round #209's run.
  - 3,323 passed: round #209's 3,320 and the 3 new cases.
  - 4 xfailed, as in round #209.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `0f7adfb`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`outer_sheets.py` is unchanged.** Its mutants were run in a worktree. Two test fields were redrawn along the
  way. A quarter arc is symmetric about 45 degrees, so it could not tell x from y in the angle. A full-circle
  winding fills every angle's bin, whichever way the angle is measured.
- **Still not reviewed from the owner's merges since round #182:** the rest of #471 (the chain
  `run_band_and_read.sh`, the snap's batches and #471's changes to `studio_band.py`), #472 to #478, #480, #483, #485,
  #488, #489, #493, #496 and #505.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 20 were run again with the new tests, and all 20 are killed.
