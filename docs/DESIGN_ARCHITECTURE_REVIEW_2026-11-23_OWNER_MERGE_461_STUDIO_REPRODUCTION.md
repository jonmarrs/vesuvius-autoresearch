# Design and architecture review — the owner's #461, the Studio reproduction check

Date: 2026-11-23. Baseline: `ac2c168` (main after round #201's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 10:12 UTC firing on 2026-11-23. Main had not moved since round #201's merge.

It takes the first part of **#461**, finding 123. The finding asks whether Studio, the reader that won PHerc. 211's
First Letters prize, reproduces the winner's map when run on this machine from the winner's own weights and input.
- `run_studio_reproduction.sh` fetches the weights and the input and checks each against the winner's recorded
  SHA-256. It then builds the winner's pinned environment and runs the winner's `inference.py`.
- `repro/first_letters/pherc0211_control/studio_reproduce.py` compares the output with the published map over the
  winner's mask. It reports the output's hash against the record, r, and the distribution of absolute differences.

The script is registered, so this round adds tests only. The rest of #461, findings 124 and 125 (Studio on our own
geometry, and on every winding of a fitted PHerc. 826 band), is for later rounds.

## What changed

### Twelve more rules of the check are tested (`tests/test_first_letters_0211_studio_reproduction.py`)

This round made 15 mutants of `studio_reproduce.py`, and #461's tests killed 3. Eight new test functions kill the
other 12. The commit that adds them says nine; the count is eight.
- **The comparison refuses a winner's map or a mask of another shape**, with its own message.
- **Pixels that are not finite are left out** of the count and of r.
- **The differences are read at their registered percentiles.** A map with 1.5% of its pixels off by 0.5 has a p99
  of 0.5. #461's maps differed everywhere or nowhere, so a p95 in its place went unnoticed.
- **A pixel at exactly 0.5 is on the upper side** of the described same-side share.
- **r = 0.99 and p99 = 0.05 exactly still reproduce.** The registered lines are "at least" and "at most".
- **The record counts the mask's pixels and hashes our output.** #461's command test checked neither, so a mask read
  as every pixel, or the winner's map hashed in place of ours, passed.
- **A missing output does not run, and an unreadable mask stops** with its reason.
- **An output holding Python objects is refused, never unpickled.** The load passes `allow_pickle=False`, so an
  output saved as an object array is refused before any comparison.

No code changed. No defect was found.

## Verified, no change needed

- **The registered numbers give the verdict.** Over 8,838,800 pixels, r is 1.0 and the 99th-percentile absolute
  difference is 0.000645. Both are well inside the lines, so `REPRODUCED`. The output's hash differs from the
  winner's recorded one, so not `EXACT`.
- **The strategy and the filing draft match the record.** Both say r 1.0 over 8.8 million pixels and 75 seconds,
  which is the inference step's recorded time. Both give 14.5 GB of GPU memory, from 14,481 MiB, the conversion round
  #199 noted.
- **The driver checks every input before running it.** It checks the weights, the input planes and the winner's
  `inference.py` against the record's SHA-256 values, and runs the record's command with `HF_HUB_OFFLINE=1`. #461's
  test checks both.

## Observations for the owner (not changed)

- **A gate file that is named but missing reads as a passing gate.** `studio_reproduce.py` takes
  `json.loads(gate)` only when the file exists, and otherwise `{"exit": 0}`. In the chain this cannot arise:
  `control_gate` writes the inference gate before the comparison step, and the comparison runs only after inference
  exits 0. Run on its own with a mistyped `--gate`, the check would compare an output whose inference may have
  failed.

## Verification

- **The touched module.** `test_first_letters_0211_studio_reproduction.py` gives 13 passed, against 5 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,107 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #201's run.
- **The 308 test modules outside the suite** give the same 24 failing ids as round #201's run, and 3,233 passed:
  round #201's 3,225 and the eight new cases. One of the 24 is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `ac2c168`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`studio_reproduce.py` is registered and unchanged.** Its mutants were run in a worktree.
- **Still not reviewed from the owner's merges since round #182:** the rest of #461 (`studio_e2e.py`,
  `studio_band.py` and their drivers), #465, #468 to #478, #480, #483, #485, #488, #489, #493 and #496.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 15 were run again with the new tests, and all 15 are killed.
