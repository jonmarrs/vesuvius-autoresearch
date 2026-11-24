# Design and architecture review — the owner's #474, the dense read at PHerc. 211

Date: 2026-11-24. Baseline: `01bb576` (main after round #216's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 01:12 UTC firing on 2026-11-24. Main had not moved since round #216's merge.

It takes **#474**, finding 131: does the twice-denser snap read better where PHerc. 211's prize was won? The four
windings went through finding 121's route twice more, once as they are (`rerun`) and once subdivided twice
(`dense2`). Each arm was carried onto the winner's surface and scored as finding 124 scored its windings.
`repro/first_letters/pherc0211_control/dense_read.py compare` scores the three arms on the cells that every arm
reaches. It requires the `f124` arm to give finding 124's r 0.8247 again on its own cells. It calls a change in r
of `dense2` over `rerun` real only beyond a margin: the larger of 0.02 and twice the re-run's noise.

The script is under `repro/first_letters/`, so this round adds tests only.

## What changed

### The comparison is run (`tests/test_first_letters_0211_dense_read.py`)

#474's tests cover the verdict table, the arms' names and the run script's text, and killed 3 of this round's 24
mutants. Seven new test functions, 9 cases, kill the other 21. They run `compare_cmd` on a small Studio map, mask and
render map. Finding 110's side and transfer are stood in for, so only the comparison's own reckoning runs. Each arm
lacks a different row of cells: no winding, no map, or no other side.
- **The arms are scored on the cells every arm reaches, and `f124` also on its own.**
  - The share is of the mask's whole cells, not of the cells the render maps also reach.
  - The transfer distances are taken over the common cells.
  - Without a distance field there is no sheet share.
  - The noise and the change keep their signs.
- **The comparison runs only once finding 124's r is given again on `f124`'s own cells.**
- **What stops the comparison, and what does not.**
  - A cosine of exactly 0 against the winner's normals stops it, and a winding without a cosine does not.
  - An unreadable mask stops it.
  - The verdict runs at exactly half the mask.
- **The sheet share** counts nodes exactly 2 voxels from the field, and has none when no node is in the field.
- **The command writes its record once, and exits 1 when the comparison does not run.**

No code changed. No defect was found.

## Verified, no change needed

- **The verdict is the registered table's.**
  - Every step exited 0.
  - `f124` gave 0.8247 on its own cells.
  - On the 442,015 of 550,482 mask cells that all three arms reach (0.803), r is 0.8304, 0.8267 and 0.8168.
  - The noise, −0.0037, keeps the margin at 0.02, and the change, −0.0099, is inside it.
  - So `DENSE_READS_SAME`, as predicted.
- **The report's described line matches the record.** The denser snap puts more of every winding on the predicted
  sheet: w033 to w036 have 0.9392, 0.8184, 0.9391 and 0.8304 of their final nodes within 2 voxels, against
  `rerun`'s 0.9047, 0.7747, 0.9104 and 0.7963.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_first_letters_0211_dense_read.py` gives 24 passed, against 15 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #216's run.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #216's run.
  - 3,388 passed: round #216's 3,379 and the 9 new cases.
  - 4 xfailed, as in round #216.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `01bb576`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`dense_read.py` is unchanged.** Its mutants were run in a worktree. The tests replace finding 110's side and
  transfer with stand-ins through `monkeypatch`; the comparison's own code runs as written.
- **Still not reviewed from the owner's merges since round #182:** #475 to #478, #480, #483, #485, #488, #489, #493,
  #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 24 were run again with the new tests, and all 24 are killed.
