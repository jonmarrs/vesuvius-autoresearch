# Design and architecture review — the owner's #461, the PHerc. 826 Studio band steps

Date: 2026-11-23. Baseline: `426519a` (main after round #203's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 12:12 UTC firing on 2026-11-23. Main had not moved since round #203's merge.

It finishes **#461** with finding 125: Studio reads every winding of a fitted band, as images for the owner to
inspect. `repro/first_letters/eligible_band/studio_band.py` has four steps:
- `orient` decides each winding's render flip from its normals, against the band's centre or, with
  `--umbilicus`, the published scroll axis.
- `summarise` writes an image of each Studio map, a contact sheet, and the share of ink over the rendered area and
  over each 380-pixel tile.
- `select` keeps the windings whose sheet-following excess is above zero.
- `stacked` measures how much of each snapped winding lies on its outer neighbour.

The script is registered, so this round adds tests only.

## What changed

### Twenty more rules of the steps are tested (`tests/test_first_letters_0826_studio_band.py`)

This round made 22 mutants of `studio_band.py`, and #461's tests killed 1. Nine new test functions, 11 cases, kill
20 of the other 21. The last is equivalent, below.
- **The scroll axis is interpolated in z from control points given in any order.**
- **Against the axis, a winding points one way even where the band's centre lies outside its curve.** A second
  winding 2,000 voxels away pulls the centre out. Against the centre, the first winding's share is then split,
  which is what made finding 125's two innermost windings fall under one half.
- **A winding exactly half inward is undecided.** `orient` exits 1, and its output is written once.
- **A node on the axis has no direction and is left out**, rather than counted with an undefined one.
- **A tile exactly at the 0.9 cover line is scored, and a probability of exactly 0.5 is ink.**
- **The summary refuses a map without exactly one render of its size.** It also takes the largest tile, gives no
  share for a winding with nothing rendered, and is written once.
- **`select` keeps positive excess only, in index order, and exits 1 when it keeps none.** With names of different
  widths, `w99` comes before `w100`.
- **`stacked` pairs only consecutive windings, and its 0.30 line is inclusive.**

No code changed. No defect was found.

### One mutant is equivalent

**Flipping at a share of at least one half, instead of above it,** changes nothing. A share of exactly 0.5 is set to
undecided before the flip line is read.

## Verified, no change needed

- **The orientation change is documented.** Finding 125 ran with the registered rule, against the band's centre.
  Its report says that rule kept w010 and w011, at 0.4931 and 0.4962, whose normals point inward against the axis,
  so their maps are not reads. The shared driver `run_studio_band.sh` now passes `--umbilicus`, as finding 126's
  amendment 1 registered before any of its data existed.
- **The registered numbers are the records'.** #461's report test checks each table against
  `reports/first_letters_0826_studio_band.json`. That includes the 11 stacked pairs, none of them at exactly 0.30, so
  the report's "more than 30%" and the code's inclusive line agree on them.

## Observations for the owner (not changed)

- **Finding 125 cannot be rerun as registered from the current driver.** The driver it ran with now orients against
  the axis for finding 126 and the band reads after it. Its record and report keep what was run.

## Verification

- **The touched module.** `test_first_letters_0826_studio_band.py` gives 15 passed, against 4 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #203's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #203's run, and 3,253 passed:
  round #203's 3,242 and the 11 new cases. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `426519a`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`studio_band.py` is registered and unchanged.** Its mutants were run in a worktree. Where a line has to be met
  exactly, three tests stub a geometry helper: a share of exactly one half, a node on the axis, and a stacked share
  of exactly 0.30.
- **Still not reviewed from the owner's merges since round #182:** #465, #468 to #478, #480, #483, #485, #488, #489,
  #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 22 were run again with the new tests: 21 are killed, and the equivalent one is
  not.
