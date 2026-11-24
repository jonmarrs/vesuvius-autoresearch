# Design and architecture review — the owner's #488, Studio on our own fit at PHerc. 343

Date: 2026-11-24. Baseline: `fe6c25b` (main after the owner's #541, which followed round #225's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 10:12 UTC firing on 2026-11-24. Since round #225's merge, the owner merged #541, which resolves
local training file URIs. It is listed below for a later round.

It takes **#488**, finding 136: does Studio draw PHerc. 343's letters on our own fit of the place, as on the recipe's
published surface? `repro/first_letters/pherc343/studio_343_own.py compare` works in three steps:
- It requires finding 127's own number, Studio on the published surface against `u`, to come out again.
- It carries Studio's maps of our windings w047 and w048 onto the published surface with finding 110's transfer.
- It scores the carried map against Studio's map of the published surface with finding 124's statistic.

The cells are those of the published image's area that the published render covers. The controls are the carried
map of our reversed planes and a 64-pixel slide.

The script is under `repro/first_letters/`, so this round adds tests only. Its run script, `run_studio_343_own.sh`,
is left for a later round.

## What changed

### The comparison, its reading frame and its command are run (`tests/test_studio_343_own.py`)

#488's tests cover the area's cells, the lattice in render pixels, and the verdict's lines and failure branches.
This round made 28 mutants of `studio_343_own.py`, and #488's tests killed 1. Six new test functions, 11 cases, kill
the other 27.
- **`compare`, on stand-ins for finding 110's side, transfer and normals.** Our windings' lattice is the published
  surface's, cell for cell, so the real carry moves each value to its own place.
  - **Finding 127 first.** Without its r again, nothing is scored, and there is no described part.
  - **The cells.**
    - The target is the area's cells that the published render covers and Studio's published map gives a value.
    - The scored cells add a winding and both carried maps.
    - The share is of the target.
    - A winding's given cells are the target's cells it is nearest to.
  - **The numbers.**
    - The registered r and controls are finding 124's statistic on those cells, with the ink line at exactly 0.5.
    - A winding of exactly 1,000 cells gets its own r.
    - The transfer distances are over the scored cells.
    - The published surface's reversed planes are its own.
    - Finding 127's numbers again use the published reversed planes.
  - **Against `u`.** The cells are those of the reading frame where both carried maps have values. The published
    surface's control uses its own reversed planes.
  - **The failure branch** scores nothing when a cosine is 0, when a winding gives no cells, or when the share is
    under the line.
- **The reading frame** refuses a render of other than 66 layers, an unreadable `u`, or one of the wrong shape.
- **The verdict** runs at exactly half the cells.
- **The command** writes its record once, prints it without the described part, and exits 1 only when the verdict
  does not run.

No code changed. No defect was found.

## Verified, no change needed

- **The verdict is the registered table's.**
  - Every step exited 0, and finding 127's r came out again: 0.6238, with the reversed planes at 0.1015.
  - 518,648 of the 556,134 target cells were scored (0.9326).
  - Both windings' normal cosines are positive (0.9974 and 0.9977). The registration stops the comparison at a
    median cosine of 0 or below: at PHerc. 343 our windings must face the way the published surface does.
  - r is 0.8999, above 0.70 and more than twice each control: 0.1765 for our reversed planes and 0.3092 for the
    largest slide. So `STUDIO_343_OWN_CLOSE`.
- **The described lines match the record.**
  - Each winding gives about the same r: w047 0.899 on 331,788 cells, and w048 0.9025 on 186,860.
  - The transfer moved cells 1.58 voxels at the median and 3.07 at p95.
  - Against `u`, on 510,650 cells, the carried map gives 0.6042 and the published surface 0.6286.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_studio_343_own.py` gives 15 passed, against 4 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #225's run. It does not run the
  touched module.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #225's run.
  - 3,494 passed: round #225's 3,483 and the 11 new cases.
  - 5 xfailed, as in round #225.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `fe6c25b`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`studio_343_own.py` is unchanged.** Its mutants were run in a worktree.
  - The tests replace finding 110's side, transfer and normal check through `monkeypatch`.
  - They also replace Studio's map reader, only to put one NaN cell into the published map. Studio's maps, the carry,
    the reading frame and finding 124's statistic run as written.
- **Still not reviewed from the owner's merges since round #182:** #488's run script, #489, #493, #496, #505, #517,
  #524 and #541.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 28 were run again with the new tests, and all 28 are killed.
