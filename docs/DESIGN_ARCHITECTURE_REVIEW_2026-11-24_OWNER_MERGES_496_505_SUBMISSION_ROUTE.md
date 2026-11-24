# Design and architecture review — the owner's #496 and #505, the submission route's re-render and catalog flags

Date: 2026-11-24. Baseline: `ba7ff07` (main after the owner's #555).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 15:12 UTC firing on 2026-11-24. Since round #230's merge, the owner merged #555, which checks
the benchmark's selected array. It is listed below for a later round.

It takes two merges that finish the submission route of `repro/first_letters/submission/`, which rounds #229 and #230
reviewed:
- **#496** adds a step 0 to the route's README. Before the first image, the found winding is rendered again at 66
  layers, because band reads now keep only the 18 that Studio reads.
- **#505** adds `catalog_flags.py`, its record and the README's count. The script counts the open-data volumes on
  which the recipe's orientation rule turns the image the wrong way, from the catalog's two flags. It also adds the
  count to the November filing draft.

The scripts are under `repro/first_letters/`, so this round adds tests only.

## What changed

### The catalog flags' edges are tested (`tests/test_catalog_orientation_flags.py`)

#505's tests check each pair of flags against `band_index`, and the count over a small catalog. They killed 6 of this
round's 14 mutants of `catalog_flags.py`. Five new test functions, 7 cases, kill 7 more; the last is equivalent,
below.
- **A flag that is not a boolean**, such as `1` or `"yes"`, is unknown.
- **A sample with null volumes, or a volume with null properties,** is counted as unknown rather than failing.
- **Every case is listed, even at zero.** With no volume that has both flags, there is no share.
- **The share is kept to four decimals.**
- **The command reads a plain catalog**, records no source when none is given, and prints the counts by case.

No code changed. No defect was found.

### One mutant is equivalent

**Testing one byte instead of two for gzip** changes nothing. A JSON file cannot start with byte 0x1f, so whatever
starts with it is not a plain catalog, and both readings fail on it alike.

## Verified, no change needed

- **#496's command is `run_render.sh`'s.**
  - The script defaults to 66 layers and names its output by its layer count, so it writes `wNNN_66.zarr`.
  - It takes `flip` as its third argument, which the band read's orient decision gives.
  - `test_first_letters_thin_render.py` pins the default, the naming and the flip.
- **The four cases agree with the band pages' rule.** For the catalog's two flags, the recipe's flips are wrong as
  `band_index.orientation` predicts. The image is turned by 180° when z runs top to bottom, and mirrored left to
  right when only the coordinates are left-handed. When both hold, it is mirrored top to bottom. #505's tests check
  this against `band_index`, and round #229's tests check `submission_inputs.py` against the same table.
- **The count and the README's claims are the record's.**
  - Of the catalog snapshot's 74 volumes, 57 have both flags. The rule holds on 18, and turns 39 wrong: 36 turned by
    180°, 2 mirrored left to right and 1 top to bottom. That is 0.6842.
  - PHerc. 0358 and 0826 fall in PHerc. 211's case, and PHerc. 0813 and 0800 in PHerc. 343's, as the README says.
  - The filing draft's "the rule holds on 18" of 57 is the same count.

## Observations for the owner (not changed)

- **Step 0 assumes the 66-layer render's path is free.** `run_render.sh` refuses an existing `wNNN_66.zarr`. The
  README says PHerc. 0358's and 0826's 66-layer renders were cut to 18 layers on 2026-11-22. If a cut render kept
  its `wNNN_66.zarr` name, step 0 stops at "exists" until that render is moved aside. The trimming log the README
  cites is on the owner's machine, so this round could not tell which.

## Verification

- **The touched module.** `test_catalog_orientation_flags.py` gives 20 passed, against 13 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,118 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 290 failing ids as round #230's run. It does not run the
  touched module.
- **The 314 test modules outside the suite** give the same 24 failing ids as round #230's run.
  - 3,611 passed: round #230's 3,604 and the 7 new cases.
  - 4 xfailed, as in round #230.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `ba7ff07`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`catalog_flags.py` is unchanged.** Its mutants were run in a worktree.
- **Not checked here:** the upstream issue the README and draft cite, and the catalog itself. This round read the
  committed record of the catalog snapshot, not the bucket.
- **#493, #496 and #505**, the submission route, are now reviewed, in rounds #229 to #231.
- **Still not reviewed from the owner's merges since round #182:** #517, #519, #524, #527, #535, #541, #543, #545,
  #547, #549, #551, #553 and #555.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 14 were run again with the new tests: 13 are killed, and the equivalent one is
  not.
