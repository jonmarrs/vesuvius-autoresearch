# Design and architecture review — the owner's #473, Studio's published tiling

Date: 2026-11-23. Baseline: `c4f8258` (main after round #214's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 23:12 UTC firing on 2026-11-23. Main had not moved since round #214's merge.

It takes the first part of **#473**: finding 128, whether Studio's published tiling is close enough to the winner's
to read bands faster. The published tiling uses 96-pixel windows written without overlap; the winner's uses a stride
of 64 with Hann blending. `repro/first_letters/pherc0211_control/studio_tiling.py` has two steps:
- the comparison scores the published tiling's map against finding 123's, over the winner's mask, with finding 123's
  `compare`, and gives the registered verdict;
- `seams`, described after the verdict, gives the mean absolute difference on the windows' edges and in their middle.

The script is under `repro/first_letters/`, so this round adds tests only. Finding 127, Studio on PHerc. 343
(`studio_343.py`), is the rest of #473.

## What changed

### Twelve more rules of the comparison are tested (`tests/test_studio_published_tiling.py`)

This round made 20 mutants of `studio_tiling.py`, and #473's tests killed 8. Five new test functions, 6 cases, kill
the other 12.
- **The seam profile takes both edges of each window, and exactly pixels 32 to 63 as its middle.** Each position
  that matters is given its own difference, so dropping either edge, or moving the middle by one pixel, changes the
  numbers. #473's test put the same difference on both edges and none just outside the middle.
- **A mask that holds no window edge gives no edge number**, rather than NaN.
- **An unreadable mask stops both commands**, with "cannot read" and the path.
- **A map holding Python objects is refused by both commands**, and is never unpickled.
- **Without the inference gate, or without the published tiling's map, the comparison does not run.** The record
  keeps the gate as found.

No code changed. No defect was found.

## Verified, no change needed

- **The verdict is the registered table's.** The record gives r 0.9396 and 0.9402 of pixels on the same side of 0.5.
  Both are below the registered 0.98 lines, so the verdict is `WINNERS_TILING_KEPT`, against the prediction
  `PUBLISHED_TILING_ADOPTED`.
- **The report's described lines match the record.**
  - The published tiling took 31 s against the winner's 75 s: 2.4 times faster.
  - The edges differ 1.69 times as much as the middle along columns (0.0649 against 0.0384), and 1.85 times along
    rows (0.0681 against 0.0368). That is the report's "1.7 to 1.9 times".
  - 1 − 0.9402 of the pixels, the report's 6%, switch side.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_studio_published_tiling.py` gives 16 passed, against 10 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #214's run.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #214's run.
  - 3,364 passed: round #214's 3,358 and the 6 new cases.
  - 4 xfailed, as in round #214.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `c4f8258`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`studio_tiling.py` is unchanged.** Its mutants were run in a worktree.
- **Still not reviewed from the owner's merges since round #182:** the rest of #473 (finding 127, `studio_343.py`
  and its driver), #474 to #478, #480, #483, #485, #488, #489, #493, #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 20 were run again with the new tests, and all 20 are killed.
