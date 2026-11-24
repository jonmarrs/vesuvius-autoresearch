# Design and architecture review — the owner's #517, finding 129's report on PHerc. 0813's band read

Date: 2026-11-24. Baseline: `8bbf49a` (main after the owner's #557).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 16:12 UTC firing on 2026-11-24. Since round #231's merge, the owner merged #542, a stand-in
`df` for the disk-guard test, and #557, which checks linked training Zarr inputs. Both are listed below for later
rounds.

It takes **#517**, the report of finding 129, PHerc. 0813's band read. It adds:
- `reports/first_letters_0813_studio_band.md`, with its records `first_letters_0813_studio_band.json` and
  `first_letters_0813_outer_sheets.json`;
- the strategy's note;
- `tests/test_first_letters_0813_studio_band_report.py`, which checks the report against its records.

PHerc. 0813 is still eligible, so the report carries numbers only. Its result is `ON_SHEETS` on finding 112's
table, and Studio read all 110 selected windings. The verdict on letters waits for the owner's eye.

There is no code in #517. This round tests the report itself.

## What changed

### Every restated number is checked (`tests/test_first_letters_0813_studio_band_report.py`)

To see how much of the report its test protects, this round made one mutant per number in the report, raising its
last digit by one. Numbers inside code spans, links and dates were left alone. #517's report test caught 221 of the
315.

Four new test functions catch 45 more. They check every place the report restates a number, not only the first:
- **The counts.**
  - The 120 windings scored, w010 to w129, of the 130 villa's fit writes.
  - The 110 selected and read, in the title, the selection, the contact sheet and the cost table.
  - The 30,000-step and 300-step fits.
- **The windings it names.**
  - w012, w013, w014 and w016, the inner windings with a trusted share under 0.4.
  - The 19 outermost, w111 to w129, in both of the sentences that name them.
  - The 91 others, in both of theirs.
- **The papyrus edge**, near w110 and past it from w115, where the outer-sheet gap changes sign, in all three places
  the report names it.
- **What it quotes from the registration.**
  - The band, z 9996 to 11496, which is the middle 1,500 slices.
  - The estimates: 3.5 h of fit; 4 h of flatten, 4 h of renders and 7 h of Studio, about 15 h; about a day and a
    half.
  - The 15 GB GPU budget, and amendment 1's 0.28.

The other 49 numbers are labels, not results:
- finding and scroll numbers, and list ordinals;
- the 0.5 probability line, the 380-pixel tile and 2 voxels;
- the p10 and p90 of a column heading, an exit code of 0, and the 18 of "18-layer".

No code or report changed. No defect was found.

## Verified, no change needed

- **The report's verdict is finding 112's table on the record.** Both lines are met, so `ON_SHEETS`, one line better
  than the registered prediction (`PARTLY_ON_SHEETS` or better). #517's tests check this, and the selection of the
  110 windings with positive excess.
- **Every restated number now agrees with the record** or with the registration, wherever it appears.

## Observations for the owner (not changed)

None this round.

## Verification

- **The touched module.** `test_first_letters_0813_studio_band_report.py` gives 18 passed, against 14 before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,118 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 290 failing ids as round #231's run. It does not run the
  touched module.
- **The 314 test modules outside the suite** give 23 failing ids, one fewer than round #231's 24.
  - The free-disk case round #196 described now passes: the owner's #542 gave the disk-guard test a stand-in `df`.
  - 3,616 passed: round #231's 3,611, the 4 new cases, and that one.
  - 4 xfailed, as in round #231.
- **The doc audit**, run alone, lists the same unresolved references as on `8bbf49a`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **The report and its records are unchanged.** The mutants were run in a worktree. Only the report's text was
  mutated, one number at a time.
- **Still not reviewed from the owner's merges since round #182:** #519, #524, #527, #535, #541, #542, #543, #545,
  #547, #549, #551, #553, #555 and #557.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
