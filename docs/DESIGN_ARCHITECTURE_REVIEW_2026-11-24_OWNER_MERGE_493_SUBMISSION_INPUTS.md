# Design and architecture review — the owner's #493, the submission inputs from a band read

Date: 2026-11-24. Baseline: `6a21b5a` (main after the owner's #551).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 13:12 UTC firing on 2026-11-24. Since round #228's merge, the owner merged #551, which records
the proofreader's launch inputs. It is listed below for a later round.

It takes **#493**, which makes a First Letters submission image from a band read with the PHerc. 343 recipe's own
image script. This round takes `repro/first_letters/submission/submission_inputs.py`, which supplies what that
script needs from our reads and what it does not measure:
- **`ink`** writes Studio's two maps of a winding as the float32 TIFFs the recipe's script reads. The reading side
  is layers 41 down to 26; the control is the reversed planes.
- **`stats`** gives the control the reading image's own display numbers, so a fainter map is not stretched to look
  like text.
- **`orient`** computes the reading orientation by the band pages' rule, with the scroll's two catalog flags.
- **`isometry`** measures how far the mesh's flattening is from isometric inside an area: edge stretch along
  rows and columns, shear, and the 3D area over the flat area.

The wrapper, `make_band_submission.sh`, is left for a later round. The module is under `repro/first_letters/`, so
this round adds tests only.

## What changed

### The inputs' refusals, edges and command are tested (`tests/test_band_submission.py`)

This round made 27 mutants of `submission_inputs.py`, and #493's tests killed 6. Eleven new test functions, 13 cases,
kill 19 more. The last 2 are equivalent, below.
- **The maps.**
  - A single infinite value is refused, and the control is checked as the reading map is.
  - Each map's record names its own source.
- **The control stats** need a single-model image made from the reading side.
- **The mesh.**
  - Its scale must be two equal positive numbers.
  - A node is invalid if any one coordinate is −1, if one is not finite, or if the mask leaves it out.
- **The flattening check.**
  - An area with nodes but no edges reports empty summaries and no area ratio, rather than failing. The area is
    recorded by name.
  - A shear either way is reported as its size.
  - A bent quad counts both of its triangles. #493's tests used flat grids, where the two triangles always have the
    same area.
- **The area argument** is four numbers, or a JSON with or without its `area` key; five numbers are refused.
- **The `orient` command** passes the two catalog flags in their places, and writes its `--out` file as it prints.

No code changed.

### One defect is pinned with a strict xfail

**`ink_tiffs` writes the reading TIFF before it checks the control.** If the control map has the wrong shape or
type, or a value that is not finite, the reading TIFF is left behind. The next run then refuses it as existing.
`test_a_control_that_fails_its_check_leaves_no_tiff_behind` shows it, and passes once both maps are checked before
either is written. The module is registered, so it is not changed.

### Two mutants are equivalent

- **Dropping the rank check** changes nothing. The shape comparison that follows already refuses a map that is not
  2D.
- **`<` in place of `<=` for "within 10%"** cannot differ for an ideal of 1.0. No double lies exactly 0.1 from 1.0,
  so no stretch sits on the line.

## Verified, no change needed

- **The isometry rules match the module's own statement.**
  - Stretch is a grid edge's 3D length over one flat step (1 / scale).
  - Shear is |90° − the angle| between the two edges at a node.
  - The area ratio is the quads' two-triangle 3D area over their flat area. The bent-quad test checks it by hand:
    1.366 for one corner lifted by a step.
- **The orientation rule is `band_index.orientation`**, which round #207 reviewed. The module loads it from
  `eligible_band/band_index.py` and passes the scroll's two catalog flags in their order.

## Observations for the owner (not changed)

- **A failing control map leaves the reading TIFF behind**, as above. A second run of `ink` then stops at "exists",
  so the output folder has to be cleared by hand.

## Verification

- **The touched module.** `test_band_submission.py` gives 26 passed and 1 xfailed, against 14 passed before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,118 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives 288 failing ids. They are round #228's 284, and 4 cases the owner's #551
  added to `test_proofreader_session.py`, which need Villa's pinned proofreader here. The suite does not run the
  touched module.
- **The 314 test modules outside the suite** give the same 24 failing ids as round #228's run.
  - 3,595 passed: round #228's 3,583 and the 12 new passing cases.
  - 4 xfailed: round #228's 3 and the new strict xfail.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `6a21b5a`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`submission_inputs.py` is unchanged.** Its mutants were run in a worktree. The tests build small meshes and
  maps under `tmp_path`.
- **Still not reviewed from the owner's merges since round #182:** #493's wrapper, #496, #505, #517, #519, #524,
  #527, #535, #541, #543, #545, #547, #549 and #551.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 27 were run again with the new tests: 25 are killed, and the 2 equivalent ones
  are not.
