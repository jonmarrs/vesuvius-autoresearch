# Design and architecture review — the owner's #425, finding 114's spacing description

Date: 2026-11-16. Baseline: `a1caddd` (main after #443).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the hourly firings from 06:13 to 20:12 UTC on 2026-11-16. The session could not run for most of
that span.

It takes **#425**, merged at 02:18 UTC on 11-16. #425 is finding 114: the recipe's spiral fit on a band of PHerc.
0826, the second unread scroll of the First Letters campaign. The decision is `NOT_ON_SHEETS`. It uses finding
112's score and table unchanged, which round #171 tested, and adds one script, `band_fit_spacing.py` in
`repro/first_letters/eligible_band/`. That script describes how far apart the fit's windings are against how far
apart the predicted sheets are. The registration says it is a description and not part of the verdict.

This round recomputed the decision and the description from the record and tested the new script.

Main moved during the round, from `3137cf7` to `a1caddd`, with #434, #435 and #443 (24 files). They are merged
into this branch without conflict, and their review is left to later rounds.

## What changed

### Twenty-seven guards of the spacing description are now tested (`tests/test_first_letters_eligible_band.py`)

The script is registered, so it is left as it is. This round made 33 mutants of it. #425's one test of it killed 6.
It covers the profile's peak and the ratio, and nothing ran the command. Eight new test functions (13 cases) kill
the other 27:

- **Each side of the profile is read from 8 voxels out.** The neighbouring sheet can be at exactly 8; 6 is still
  the winding's own sheet. A dip at 8, or a trough at 0, is not part of what the rise must clear.
- **The two directions are averaged**, a tie goes to the nearer offset on either side, and a rise only as high as
  the dip before it is no rise.
- **There is no sheet spacing without offsets between 0 and 8.**
- **The summary's percentiles are the ones they are named**, and the profile is rounded to four places.
- **The command pools raw windings and measures consecutive ones.** It skips spliced twins and folders without a
  mesh, opens group 1 of the distance field, refuses an output that exists, and gives the right spacing on
  windings 16 voxels apart.
- **The profile reads every fourth node that has a normal, moved along its own normal.** A mutant that sampled
  every other node, or took nodes without a normal, or paired a node with its neighbour's normal, passed #425's
  test.
- **A node counts only where all 25 offsets have a value**, and a node on the face of a sheet is inside it.
- **A pair of windings too far apart sideways has no spacing**, and the command writes nothing when no node is in
  the field.

No code changed.

## Verified, no change needed

- **The decision recomputes from the record.** `verdict(record["steps"], record["smoke"], record["full"])` gives
  the stored verdict, and both stored flags are what `holds` gives:
  - all three steps exited 0, and each fit has 120 scored windings against at least 60;
  - the floor, the 300-step fit's median excess, is 0.0005 against at most 0.03;
  - P1 and P2 both fail: a median excess of 0.0043 against at least 0.07 and 0.03, and 59.17% of windings
    positive against at least 80% and 65%.
- **The description recomputes.** `sheet_spacing` on the record's profile gives 14.0 voxels, and the ratio is the
  median winding spacing of 11.55 over it, 0.825.
- **The report's spacing paragraph matches the record**: 11.6 voxels over 119 pairs, 6.4 to 14.9, a peak of 0.171
  at zero, 0.133 and 0.139 at 14 voxels, and the ratio of 0.825.
- **The order of events.** The registration (acf767e, 13:28 PST on 11-14) precedes the results (e41301b, 19:01
  PST on 11-14). Nothing in `repro/first_letters/eligible_band/` changed between the two. The spacing script and
  its launcher are unchanged since.
- **The report is candid about its result.** It says the registered prediction (`ON_SHEETS`) was wrong. It says
  the registered median over 120 windings mixed two questions, whether the windings follow sheets and whether 130
  is the right number of them, and calls that a flaw in the rule. It marks its range of w020 to w079 as chosen
  after seeing the table.

## Observations for the owner (not changed)

- **The band verdict command still fails on a full fit with no scored winding.** Rounds #171 and #173 reported
  it. On `a1caddd` the command still raises `KeyError: 'excess_median'` for that case and writes no record.
  Findings 112, 114 and 115 all use the script, so the next band will too.
- **"0.112 at 6 voxels" is the mean of the two sides.** The record has 0.1115 at −6 and 0.1128 at +6. The figures
  for 14 voxels in the same sentence are one side each.

## Verification

- **The touched module.** `test_first_letters_eligible_band.py` gives 46 passed, against 33 on `a1caddd`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,020 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #173's run.
- **The test modules outside the suite.** The 262 modules give the same 23 failing ids as round #173's run, and
  2,652 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `a1caddd`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Finding 114 was checked from its record, not rerun.** The run needs the scan, villa's fit and a GPU.
- **Not reviewed in #425:** `run_spacing.sh`, the report beyond its verdict and spacing sections, and the edits to
  `docs/RESEARCH_STRATEGY.md`.
- **Still not reviewed:** #427 (finding 115), #433, #434, #435, #436, #437 and #443, #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample** of the script. Both of the touched test modules passed here before the mutants were
  run. The 27 survivors were run again against the new tests; the 6 that #425's test killed were not.
