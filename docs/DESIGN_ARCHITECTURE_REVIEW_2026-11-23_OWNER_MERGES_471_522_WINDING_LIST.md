# Design and architecture review — the owner's #471 and #522, the read's winding list and the UAMT note

Date: 2026-11-23. Baseline: `5a7170b` (main after round #212's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 21:12 UTC firing on 2026-11-23. Main had not moved since round #212's merge.

It finishes **#471** and takes **#522**.
- **#471**, finding 126, let `repro/first_letters/eligible_band/run_studio_band.sh` read only the raw windings that
  `STUDIO_WINDINGS` names: the windings `studio_band.py select` chose before any ink.
- **#522** marks the UAMT strategy item's launcher as archived in `docs/VILLA_STRATEGY.md`, a one-line change.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### The winding list is run, not only read (`tests/test_first_letters_0358_band.py`)

#471's test of the list checks that the script uses `grep -Fxf`, which killed 1 of this round's 4 mutants. Two new
test functions run the list's block of the script on a mesh folder that holds w010, w0100, w011 and w012, a spliced
twin and a note. They kill all 4.
- **Without a list, every raw winding is read, and only raw windings.** The spliced twin and the note are left out.
- **With a list, only the named windings the fit wrote are read, each named whole.** A named w010 does not bring in
  w0100, and a named winding the fit did not write is not read.
- **A list that names none of the fit's windings is refused** with "no windings to read", exit 2.

No code changed. No defect was found.

## Verified, no change needed

- **#471 is now reviewed.** Rounds #209 to #213 took `band_record.py`, `outer_sheets.py`, the chain, the snap's
  batches and this list. Round #204 had taken the select and stacked steps of `studio_band.py`, and #471's tiling
  choice has its own run test in `tests/test_first_letters_0813_band.py`.
- **#471's scroll entries agree with the catalog.**
  - `env.sh` gives PHerc. 0358 anticlockwise, from z top to bottom and right-handed coordinates.
  - It gives PHerc. 0813 clockwise, from z bottom to top and right-handed coordinates.
  - The catalog record #505 added, `reports/evidence/catalog_orientation_flags_2026-11-22.json`, puts PHerc. 0358
    with PHerc. 0211 and 0826, which the recipe's rule turns by 180 degrees, and PHerc. 0813 with PHerc. 0343,
    where the rule holds.
- **#522's note matches the tree.** The UAMT launcher is at `scripts/archive/launch_uamt.py`, moved there by #494 on
  2026-11-23, the date the heading gives. No document points to its old path.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_first_letters_0358_band.py` gives 24 passed, against 22 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #212's run.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #212's run.
  - 3,350 passed: round #212's 3,348 and the 2 new cases.
  - 4 xfailed, as in round #212.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `5a7170b`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_studio_band.sh` is unchanged.** Its mutants were run in a worktree. The tests run the one block, with
  `LC_ALL=C` so that `ls` lists the windings in the same order everywhere.
- **Still not reviewed from the owner's merges since round #182:** #472 to #478, #480, #483, #485, #488, #489, #493,
  #496, #505 and #517.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 4 were run again with the new tests, and all 4 are killed.
