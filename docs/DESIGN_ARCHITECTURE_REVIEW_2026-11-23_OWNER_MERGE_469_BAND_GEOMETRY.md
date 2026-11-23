# Design and architecture review — the owner's #469, the band read's geometry

Date: 2026-11-23. Baseline: `3a8392b` (main after the owner's #505).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 16:12 UTC firing on 2026-11-23. Main had moved since round #207's merge: the owner merged #505,
which adds the submission route, the orientation defect reported upstream and Studio's skip to the November filing
draft, with a record of the catalog's orientation flags. #505 is listed below for a later round.

It takes the second part of **#469**: `repro/first_letters/eligible_band/band_geometry.py`, described after each
band read. For each winding of an arm it measures:
- which way the final and snapped windings' normals point, against the published scroll axis and against the band's
  mean node;
- how much of each lies within 2 voxels of the predicted sheet, overall and by radius tercile;
- how much of the final winding lies within 2 voxels of the snapped winding's triangles;
- the trusted share, on the sheet with render layers running outward, and a trust mask per winding.

The script is under `repro/first_letters/`, so this round adds tests only. `band_record.py` is the rest of #469.

## What changed

### Twenty-five more rules of the geometry are tested (`tests/test_first_letters_band_geometry.py`)

This round made 36 mutants of `band_geometry.py`, and the existing tests killed 11. Fifteen new test functions, 23
cases, kill the other 25. A sixteenth function is a strict xfail, below.
- **The senses are checked absolutely.** With theta and z rising along columns and rows, a winding's normals point
  away from the axis. The existing tests took their expected classes from `inward_share` itself, so reversing its
  sign passed them.
- **The axis centre is interpolated in x and y along z.**
- **The distance to a triangle is right from each of its seven regions**: beyond each corner, beyond each edge, and
  over the face.
- **The search over triangles.**
  - A candidate that gives NaN does not hide the others. The test is a cell with two corners on one point, whose
    first triangle has an edge of zero length.
  - Cells are split between the second-row and second-column corners, as VC splits them. A bent cell tells the two
    splits apart.
  - A cell with a missing corner has no triangles, and a grid with no whole cell gives an infinite distance.
  - A grid of one cell has two triangles, fewer than the 12 candidates searched.
- **The lines and the field's edge.**
  - A node exactly 2 voxels from the sheet counts as near it, and one exactly at 0 as inside it.
  - Nodes outside the field are counted apart, with no share when none is inside it.
  - Each radius tercile counts its own nodes within the field, and has no share when none of them is in the field.
- **The record's parts.**
  - The masks folder is made with its parents.
  - The band centre is the mean of the nodes that exist, and the band-centre share is taken against it.
  - The snapped numbers are read from the snapped winding.
  - The record is written once.

No code changed.

### A strict xfail marks a mislabel in the summary

The summary's `rendered_against_the_axis_rule` names the windings whose share inward against the axis and share
inward against the band centre fall on opposite sides of one half. It does not read the render. That names the
windings rendered against the axis rule only when the render followed the band centre, as finding 125's did. Since
finding 126, the band reads orient against the axis with `--umbilicus`. On such a read, a winding where the band
centre disagrees with the axis was rendered by the axis rule, yet the list names it as rendered against it.

A scratch probe confirmed it. A small winding near the axis was rendered "keep", as its axis share of 0.0 says,
beside a large one far out that pulls the band's mean beyond it. The list named the small winding. The new test is
that band, and it is a strict xfail until the list is taken from the renders.

## Verified, no change needed

- **The triangle distance is Ericson's.** `_closest_on_triangles` follows Real-Time Collision Detection, 5.1.5: the
  same products, the same six regions in the same order with the first winning, and the face's barycentric point.
  `distance_to_triangles` skips a degenerate candidate's NaN with `fmin`.
- **Finding 125's geometry section matches its record.** Its numbers are the summary in
  `reports/first_letters_0826_studio_band.json`:
  - inward against the axis, median 0.8895 (0.8433 to 0.958) final and 0.9563 snapped, and 0.6621 against the band
    centre;
  - within 2 voxels, 0.7737 snapped and 0.6676 final; inside, 0.5423 and 0.4334;
  - the terciles, 0.7866, 0.6613 and 0.5405, and on the snapped triangles, 0.9728;
  - the trusted median, 0.6079.

  There the list is w010 and w011, which were rendered against the axis rule, because finding 125 oriented against
  the band centre.
- **A tercile with no value is handled.** The summary's medians leave out `None`, so a winding partly outside the
  field does not stop the record. Round #206 found that `dense_snap.py`, which takes the same tercile measure, has
  no such filter.
- **The mask's values are the docstring's**: 255 trusted, 128 the other side, 64 off the sheet, and 0 where a node has
  no normal.

## Observations for the owner (not changed)

- **`rendered_against_the_axis_rule` should be taken from the renders before the next band record.** Findings 126 and
  after orient against the axis. The PHerc. 0813 and 0800 registrations run `band_geometry.py` after their reads. On
  PHerc. 0826 the band's mean lay off the axis, which is why their rule changed. A band whose mean disagrees with
  the axis on a winding would see that winding named as rendered against the axis rule, though it was rendered by
  it. PHerc. 0358's record lists none, and its report test checks each render against the axis share directly.
  Comparing each winding's `render` with its axis share (flip above one half, keep below) would give finding 125's
  w010 and w011 as now, and none for an axis-rendered band.

## Verification

- **The touched module.** `test_first_letters_band_geometry.py` gives 30 passed and 1 strict xfail, against 7 passed
  before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, now 1,109 files with #505's two, with
    `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #207's run.
- **The 309 test modules outside the suite**, round #207's 308 and #505's new one, give the same 24 failing ids as
  round #207's run.
  - 3,314 passed: round #207's 3,276, #505's 15 new cases (13 in its new module, 2 in the filing draft's)
    and this round's 23.
  - 4 xfailed: round #207's three and this round's.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `3a8392b`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`band_geometry.py` is unchanged.** Its mutants were run in a worktree. The mislabel was confirmed in a scratch
  probe before its test was written.
- **Still not reviewed from the owner's merges since round #182:** the rest of #469 (`band_record.py`), #471 to
  #478, #480, #483, #485, #488, #489, #493, #496 and #505.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 36 were run again with the new tests, and all 36 are killed.
