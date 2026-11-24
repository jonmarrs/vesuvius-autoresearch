# Design and architecture review — the owner's #485, Studio's depth sweep

Date: 2026-11-24. Baseline: `0728ea4` (main after round #223's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 08:12 UTC firing on 2026-11-24. Main had not moved since round #223's merge.

It takes **#485**, finding 135: at what depth does Studio read our geometry best, where PHerc. 211's prize was won?
`repro/first_letters/pherc0211_control/depth_sweep.py` works in three steps:
- **`planes`** moves Studio's 16 input planes D layers along the 66-layer frame, for D from −8 to +8.
- **`compare`** carries each of two arms onto the winner's surface once, and scores every shift's map there with
  finding 124's statistic. Each arm is scored on the cells that every one of its shifts reaches. The arms are
  finding 124's windings (`e2e`) and finding 134's three-pass windings (`dense2s3`).
- **`compare343`** describes the same sweep on PHerc. 343's published surface, with finding 127's statistic.

The verdict takes the shift with the largest r summed over the two arms. A shift other than 0 reads better only if
it gains 0.02 in both arms.

The scripts are under `repro/first_letters/`, so this round adds tests only.

## What changed

### The comparisons, the carry and the command are run (`tests/test_studio_depth_sweep.py`)

#485's tests cover the shifted planes, the chosen shift, the verdict's branches and the half widths. This round made
40 mutants of `depth_sweep.py`, and #485's tests killed 5. Fourteen new test functions, 19 cases, kill the other 35.
- **The edges.**
  - The deepest inward shift, −26, reaches layer 0, and −27 is refused.
  - A 16-bit render is refused.
  - The summed r is compared at four decimals, so 0.1 + 0.2 ties with 0.3 and the smaller shift wins.
  - The verdict runs at exactly half the mask.
- **An arm's cells** need a winding, a reversed map and every shift's map.
- **`carry_arm`** transfers the arm once. It reads D = 0 and the reversed planes from the arm's own maps, and every
  other shift from `SWEEP_DIR/d±D`.
- **`compare`**, on stand-ins for finding 110's side and transfer like those rounds #217 and #221 used.
  - Each arm is scored on the cells that all its shifts reach. The share is of the mask's whole cells.
  - Finding 124's own cells are `e2e`'s at D = 0, which another shift's missing row does not narrow.
  - A winding of exactly 1,000 cells gets its own r. Transfer distances are taken over each arm's cells.
  - The verdict runs once finding 124's r is given again, and is the registered rule's.
  - The sheet share is the one the distance field gives.
  - A cosine of 0, or a winding with no cells, stops the comparison.
  - An unreadable mask stops it.
- **`compare343`**, on a small render, ink image and maps.
  - Every shift is scored with finding 127's statistic, on the cells every layer renders. The ink line is exactly
    0.35, on the ink image read as v / 255.
  - D = 0 reads the given map, and the control reads the reversed one.
  - An unscored shift is never the best.
  - A render of 65 layers, an unreadable or misshapen ink image, or a misshapen map is refused.
- **The command** needs both arms and writes its record once. It prints the record without the described parts, and
  exits 1 only when the verdict does not run.

No code changed. No defect was found.

## Verified, no change needed

- **The verdict is the registered table's.**
  - Every step exited 0, and every winding's normal cosine is between −0.996 and −0.999.
  - `e2e` gives finding 124's 0.8247 again at D = 0, on the same 457,405 cells as finding 134's `f124` arm. Each arm
    reaches 0.83 of the mask: 0.8309 and 0.8327.
  - The summed r is largest at D = 0, 0.8247 + 0.8135 = 1.6382, against 1.6265 at −1 and 1.6217 at +1.
  - So `DEPTH_ZERO_BEST`, with no gain.
- **The described lines match the record.**
  - r falls to half its D = 0 value at +6 outward in both arms. Inward it stays above half: at −8, r is 0.4552 and
    0.4644, against halves of 0.4124 and 0.4068.
  - At PHerc. 343, D = 0 gives finding 127's 0.6238 again. The best shift is +1, at 0.6274, and r falls to half at
    +8 (0.2832).
- **The cosine rule is this finding's own.** Findings 131 and 134 let a winding without a cosine through. Finding
  135's registration stops the comparison when a winding gives no cells, and `compare` does: a cosine of `None`
  stops it, as one of 0 or above does.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_studio_depth_sweep.py` gives 26 passed, against 7 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #223's run. It does not run the
  touched module.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #223's run.
  - 3,468 passed: round #223's 3,449 and the 19 new cases.
  - 4 xfailed, as in round #223.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `0728ea4`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`depth_sweep.py` is unchanged.** Its mutants were run in a worktree.
  - `compare`'s tests replace finding 110's side and transfer, and the sheet share, through `monkeypatch`.
  - `carry_arm`'s test replaces its readers, to see which files it reads.
  - One `compare343` test replaces finding 124's statistic with a table, because a constant map stops the statistic
    before it can give no r.
- **`pherc0211_control/run_depth_sweep.sh` is left for a later round.** No test runs or reads it.
- **Still not reviewed from the owner's merges since round #182:** #485's run script, #488, #489, #493, #496, #505,
  #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 40 were run again with the new tests, and all 40 are killed.
