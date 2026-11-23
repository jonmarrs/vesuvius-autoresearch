# Design and architecture review — the owner's #461, Studio reading our own geometry

Date: 2026-11-23. Baseline: `86fcae8` (main after round #202's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 11:12 UTC firing on 2026-11-23. Main had not moved since round #202's merge.

It takes the second part of **#461**, finding 124: Studio reading our own geometry at the place where PHerc. 211's
prize was won. `repro/first_letters/pherc0211_control/studio_e2e.py` has two steps:
- `planes` cuts Studio's 16-plane input from one of our renders: layers 41 down to 26 of the 66-layer frame, or the
  reverse for the other-side control.
- `compare` carries Studio's maps of finding 121's four windings onto the winner's surface by finding 110's
  transfer, and scores them with finding 118's numbers. It also describes Studio on our render of the winner's own
  surface.

The script is registered, so this round adds tests only. Finding 125, the PHerc. 826 band, is the rest of #461.

## What changed

### Eighteen more rules of the comparison are tested (`tests/test_first_letters_0211_studio_e2e.py`)

This round made 21 mutants of `studio_e2e.py`, and #461's tests killed 3. Nine new test functions kill the other 18.
The commit that adds them says ten; the count is nine.
- **The planes refuse a render that cannot give them.** That covers a 10-layer render without layers 26 to 41, an
  odd-layered one, and a 16-bit one. A centred 20-layer render is enough, and the planes are written once.
- **A Studio map of another size is refused.**
- **The verdict at its other edges.**
  - A cell share exactly at the line runs.
  - r exactly twice the other side clears it, and the other side counts by its absolute value.
  - A missing other side does not run.
- **`r_with_background` keeps our map's background in.**
- **Our render's map and the pipeline's are compared on the same cells.**
  - With our render's Studio map equal to the winding's, the transfer carries the one onto the other exactly, and
    they agree at r 1.0.
  - A hole in our render's map leaves those cells out of every number.
- **Each part's r is the pipeline's, and the transfer's median lies below its 95th percentile.**
- **A zero cosine and an unreadable mask stop the comparison.**
- **The cell share, a winding's cell count and the ink line are each measured exactly at their lines.**

No code changed. No defect was found.

## Verified, no change needed

- **The registered numbers give the verdict.** The carried maps give r 0.8247 on 0.8309 of the winner's mask
  cells. The controls are −0.0471 for the reversed planes and 0.1141 for the largest slide. r is past 0.70 and more
  than twice each control, so `STUDIO_E2E_CLOSE`.
- **The strategy matches the record.** It gives r 0.82, controls −0.05 and 0.11, and 0.97 for Studio on our render
  of the winner's surface. The record has 0.9745.
- **A thinner render can serve.** The planes are taken through `render_frame.frame_index`, so a centred render with
  an even layer count that holds layers 26 to 41 gives the same 16 planes as the full 66-layer render.

## Observations for the owner (not changed)

- **"r (background in)" keeps only our map's background.** `score` puts it as the correlation of our map, raw,
  with `theirs`, the winner's map after its broad background was taken off. The report's table heads that column
  "r (background in)": 0.7383 for the carried maps and 0.8368 for our render. With the winner's background in too,
  the numbers could differ. They are described, not registered, and the report says none of them changes the
  verdict.
- **The registered cells depend on our render's map as well.** The cells are restricted to where Studio's map of our
  render of the winner's surface is finite. That map is described, not registered. In the run it removed
  none: the registered cells are the same 457,405 as finding 121's. A hole in it would shrink the registered
  comparison.

## Verification

- **The touched module.** `test_first_letters_0211_studio_e2e.py` gives 16 passed, against 7 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #202's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #202's run, and 3,242 passed:
  round #202's 3,233 and the nine new cases. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `86fcae8`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`studio_e2e.py` is registered and unchanged.** Its mutants were run in a worktree.
- **Still not reviewed from the owner's merges since round #182:** the rest of #461 (`studio_band.py` and
  `run_studio_band.sh`, finding 125), #465, #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 21 were run again with the new tests, and all 21 are killed.
