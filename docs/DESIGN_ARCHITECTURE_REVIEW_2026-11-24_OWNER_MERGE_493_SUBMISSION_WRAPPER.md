# Design and architecture review — the owner's #493, the submission wrapper

Date: 2026-11-24. Baseline: `187a81d` (main after the owner's #553).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 14:12 UTC firing on 2026-11-24. Since round #229's merge, the owner merged #553, which checks
local Zarr metadata. It is listed below for a later round.

It finishes **#493** with `repro/first_letters/submission/make_band_submission.sh`, which round #229 left. The
wrapper makes a First Letters submission image from one winding of a band read, and its control, with the PHerc. 343
recipe's own image script, run unchanged from its clone at the pinned commit. Its steps:
- `ink` writes Studio's two maps as the recipe's TIFFs;
- the mesh's geometry files are hashed, for the script to check;
- `orient` gives the flips by the band pages' rule;
- `image` draws the reading side;
- `stats` takes the reading image's numbers for the control, and `control` draws the reversed planes with them;
- `isometry` measures the flattening in the area;
- a manifest hashes every input and output.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### The wrapper is run end to end (`tests/test_band_submission.py`)

#493's one wrapper test covers its first three refusals, and killed 1 of this round's 21 mutants. Five new test
functions, 9 cases, run the wrapper end to end with stand-ins:
- `git` reports the recipe's pinned commit;
- the recipe's image script is a stand-in that records its arguments and writes the reading image's sidecar;
- our own `submission_inputs.py` runs as written.

They kill 19 more. The last is equivalent, below.
- **The image and its control** get:
  - the flips from `orientation.json`;
  - the area as col0, row0, col1, row1, from a JSON with or without its `area` key;
  - `--max-cm2` and `--forbid-words` as given;
  - the flipped-render note only for a flipped render;
  - the umbilicus only in the script's own frame, where z runs bottom to top and coordinates are right-handed.
- **The image** reads the reading-side TIFF and gets the rows, the letters and the letter-size table. **The control**
  reads the reversed-plane TIFF, with the reading image's stats and `--allow-blind`, and no annotations.
- **The geometry sums** include the mask when the mesh has one. **The isometry** is measured in the same area.
- **The manifest** hashes each file input, records a directory or a "-" as no hash, and lists the commands.
- **A failed step** stops the wrapper before the control and the manifest.
- **The refusals**, before anything is written:
  - fewer than nine paths;
  - no voxel size;
  - a recipe script that differs from its commit;
  - a missing umbilicus or rows file.

No code changed. No defect was found.

### One mutant is equivalent

**Not excluding `manifest.json` from the manifest's outputs** changes nothing. The outputs are listed before the
manifest is written, so it is never among them.

## Verified, no change needed

- **The wrapper passes `submission_inputs.py` what round #229 tested.** The render's height and width go to `ink`,
  the catalog's two flags go to `orient`, and the raw-frame area goes to `isometry`.
- **The umbilicus rule is the wrapper's own documentation.** The recipe's script measures the reading orientation
  only in PHerc. 343's frame, so the wrapper lets it cross-check there. Elsewhere the wrapper's flips are the only
  ones.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_band_submission.py` gives 35 passed and 1 xfailed, against 26 passed and 1 xfailed
  before. Two runs in a row gave the same.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,118 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives 290 failing ids. They are round #229's 288, and 2 cases the owner's #553
  added to `test_proofreader_launcher.py`, which need Villa's pinned proofreader here. The suite does not run the
  touched module.
- **The 314 test modules outside the suite** give the same 24 failing ids as round #229's run.
  - 3,604 passed: round #229's 3,595 and the 9 new cases.
  - 4 xfailed, as in round #229.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `187a81d`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`make_band_submission.sh` is unchanged.** Its mutants were run in a worktree. The tests write their stand-ins and
  inputs under `tmp_path`: `git`, the recipe's Python and the recipe's script. They never touch a real recipe clone.
- **#493 is now reviewed**, in rounds #229 and #230.
- **Still not reviewed from the owner's merges since round #182:** #496, #505, #517, #519, #524, #527, #535, #541,
  #543, #545, #547, #549, #551 and #553.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 21 were run again with the new tests: 20 are killed, and the equivalent one is
  not.
