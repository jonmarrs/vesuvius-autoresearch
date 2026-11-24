# Design and architecture review — the owner's #473, Studio at PHerc. 343's published letters

Date: 2026-11-24. Baseline: `ef04792` (main after round #215's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:12 UTC firing on 2026-11-24. Main had not moved since round #215's merge.

It finishes **#473** with finding 127: does Studio draw PHerc. 343's published letters, on a scroll it was not
trained on? `repro/first_letters/pherc343/studio_343.py compare`:
- crops Studio's maps of the recipe's published surface to the published image's area, and mirrors them as the
  sidecar records;
- scores them against `u`, the recipe's ensemble ink image, with finding 118's r, against the reversed planes and a
  64-pixel slide;
- sets the lines from how well each of the recipe's four models agrees with the other three;
- describes, afterwards, Studio's ink in each of the 18 published letter boxes.

The script is under `repro/first_letters/`, so this round adds tests only. Round #215 took finding 128, the rest of
#473.

## What changed

### Twenty more rules of the comparison are tested (`tests/test_first_letters_343_studio.py`)

This round made 26 mutants of `studio_343.py`, and #473's tests killed 5. Seven new test functions, 15 cases, kill
20 of the other 21. The last is equivalent, below. The commit that adds the tests says twenty-one in its title; the
count of mutants they kill is twenty.
- **The verdict at its other edges.**
  - A cell share exactly at the 0.5 line runs.
  - A missing other side or slid control does not run.
  - A negative slide counts by its size.
  - r exactly twice the other side clears it, and r exactly at the 0.20 line is `STUDIO_343_PARTLY`.
- **A recipe map is read as the recipe's image script reads it.**
  - A TIFF reads as clip((v − 64) / 128, 0, 1) and must have the render's shape.
  - A PNG reads as v / 255, resized to the render.
  - An unreadable PNG is refused.
- **The letter boxes.**
  - A box's fractional edges are rounded.
  - `u` exactly at the overlay's 0.35 line counts as drawn.
  - A box with no valid pixel is left out of the scored boxes.
  - A box at Studio's own share over the area is not counted as above it.
- **What stops the comparison.**
  - A render of other than 66 layers, or an unreadable or misshapen ink image, stops it.
  - A pixel that any one layer leaves empty is invalid.
  - With half the area's cells left, the comparison runs. With fewer, it records "too few valid cells" and does
    not run.
- **The reversed image shows the reversed planes' map**, not the forward one.

No code changed. No defect was found.

### One mutant is equivalent

**Leaving the drawn cells unrestricted to the compared cells** changes nothing. Finding 120's `overlap`, used for both
the overlap and its slid control, intersects the ink with the compared cells itself.

## Verified, no change needed

- **The verdict is the registered table's.**
  - 63.83% of the area's cells are valid, above the 0.5 line.
  - r is 0.6238, above the 0.41 line.
  - r is more than twice each control: the reversed planes give 0.1015 and the largest slide 0.2146.
  - So `STUDIO_343_AGREES`, as predicted.
- **The lines are the registered ones.** The record's leave-one-out values are the registration's: dense_native
  0.6195, Hecate 0.41, ink_9um seed 42 0.525 and seed 43 0.5152. #473's test checks the registration's table.
- **The described lines match the record.**
  - Studio's ink share over the valid area is 0.1453, and 0.0574 with the planes reversed; `u` draws 0.1485.
  - In all 18 letter boxes, Studio's ink share is above its share over the whole area.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_first_letters_343_studio.py` gives 30 passed, against 15 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #215's run.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #215's run.
  - 3,379 passed: round #215's 3,364 and the 15 new cases.
  - 4 xfailed, as in round #215.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `ef04792`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`studio_343.py` is unchanged.** Its mutants were run in a worktree.
- **#473 is now reviewed**, in rounds #215 and #216.
- **Still not reviewed from the owner's merges since round #182:** #474 to #478, #480, #483, #485, #488, #489, #493,
  #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 26 were run again with the new tests: 25 are killed, and the equivalent one is
  not.
