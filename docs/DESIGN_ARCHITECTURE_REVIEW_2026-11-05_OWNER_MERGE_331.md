# Design and architecture review — the owner's #331

Date: 2026-11-05. Baseline: `c15e4790` (main after #331).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12 UTC firing.
- **#331 records the two GPU studies that #330 registered.**
  - Finding 103 is the seed-heading confirmation; finding 104 is the refit-retry pilot.
  - Both ran on 2026-11-03 from the registration commit, f7145c5d.
  - An unregistered presence screen follows finding 104.
  - Each result was committed after its run: 963bac1c at 15:17 PST, 73189262 at 17:10 and 226f933d at 17:59.

This round corrects one line of finding 104's report and adds two tests.

## What changed

- **Finding 104's limits counted finding 103 as development data** (`reports/neural_tracer_refit_retry.md`).
  - The line said "Findings 91–103 developed on these 21 cubes". Finding 103 traced ten cubes outside the 21; its
    smoke only reproduced one of them. The same report says so under "What it changes".
  - The line now says 91–102, as findings 101 and 102 count theirs.
  - The new test checks that the two cube sets are disjoint. It fails on the old line.
- **Five correct statements had no test** (`tests/test_seed_heading_confirmation_report.py`,
  `tests/test_neural_tracer_refit_retry_report.py`).
  - Finding 103's neighbouring cube: in the padded CT, `s5_16997_03497_03997_256` shares a 12 × 12-voxel column with
    finding 100's `s5_16997_03997_04497_256`. The cubes themselves do not overlap. Finding 100's gain there was 1.28×.
  - Finding 103's limits: seven of the ten cubes have in-sample presence, three are held out, and all are from
    Scrolls 1 and 5.
  - Finding 104's "All 21 baseline runs".
  - Finding 104's net change of 159,157, which the screen's 441,586 added voxels exceed.
  - Each statement now has a test that fails when its figure is changed.

## Verified, no change needed

- **The registered code ran unchanged.** These files are byte-identical at f7145c5d and on main:
  - both studies' scripts;
  - the refit launcher;
  - both chains;
  - the modules they import: `villa_seed_heading_rerun`, `neural_tracer_steep_heading` and
    `neural_tracer_ct_context`.
- **Both verdicts recompute exactly.** The registered `verdict` and `outcome`, run on each record's rows and run
  records, give the recorded verdict, status and reading, field for field.
  - **Finding 103:** status OK, decision `NO_HIGH_SKIP_CUBE`.
    - P1 and P2 held. P3 went untested: the highest skip share is 0.167. P4 missed (ρ 0.21). P5 held.
    - The smoke passed, and `after` skipped no dot on any cube.
  - **Finding 104:** status OK.
    - P1 missed: the median held-out gain is 0.003. P2 missed: merges rose by 219, against the floor's 35. P3 held on
      9 of 10.
    - All 21 baseline rows reproduced, the floor is 0.008, and the smoke records the retry off.
- **The records name what ran.**
  - Finding 103's `data_sha256` equals the registered `DATA_SHA256` for all ten cubes. Its villa commit is a prefix of
    `VILLA_SHA`.
  - Finding 104's baseline rows equal those from `neural_tracer_steep_heading.baseline()`. Its ceiling gains equal
    finding 102's record.
- **The report figures are bound.**
  - I made 67 mutants across:
    - the two reports;
    - the strategy and the villa draft;
    - both registrations;
    - finding 102's note.
  - 61 of the 67 failed a test as #331 committed them.
  - The six that passed are the wrong line and the five statements above. All eight mutants now fail, two added for
    the neighbouring cube's gain and the scrolls.
  - Finding 104's "two-thirds" of confidence stops off the reference is finding 101's figure, which that report's
    tests bind.
- **Two of #330's observations did not arise in the run.**
  - Every cube had seed dots and a nonzero baseline, so `skip_share` never divided by zero.
  - The chain ran `presence` from the registration commit, which checked every image against its registered hash. So
    the images presence read were byte copies of the release files.
- **The presence screen.**
  - **Frames.** It reads finding 91's presence level in the cube frame (`T/presence`), not the padded copy. The labels
    are in the cube frame too, so the two align.
  - **Its computations.**
    - Its on-reference test reproduces every baseline row's predicted length and precision.
    - Its AUC is the exact Mann–Whitney probability.
    - Its pooled figures are the sums of the cubes'.
  - **"Only at 240" holds.** At every threshold up to 224, the share of kept additions on the reference (0.432–0.543)
    is below the baseline's 0.553.
  - **Its standing.** Its report section and the strategy line say it is not registered and decides nothing.

## Observations for the owner (not changed)

- **The screen checks the baseline runs it reads, not the refit runs.**
  - `reproduces_baseline_row` ties each baseline run to finding 104's row. Nothing ties the refit runs under `--work`
    to the rows finding 104 scored.
  - The record is consistent with those rows:
    - on each cube, the added voxels exceed the net change in predicted length;
    - the on-reference added voxels exceed the net change in on-reference length.
  - If the screen is re-run, a refit-row check like the baseline's would close this gap.
  - The record is written once, so the script stays as it ran.
- **The screen's record names no ScrollGT commit.** `gt_near` imports ScrollGT's private `_resample_fiber`. The
  baseline-row check would catch a scorer that moved.
- **The villa re-check at main of the day is still open**, as finding 103 says: the draft's "Before posting" step 3.
- **#330's other observations stand.** No loop-pausing wrapper is committed for either chain, although both reports
  say the loop was stopped. The "on any of the ten" wording did not arise, since no cube had a zero baseline.

## Verification

- **The two studies' modules, the two report modules and the screen's module:** 84 passed, with the added tests.
- **Ruff and mypy.** Ruff 0.9.10 `check` and `format` are clean on the changed test files. Mypy is clean over the whole
  repository: 884 files, which includes #331's four.
- **The standard suite** gives the same failures as round #145:
  - the 43 standing failures;
  - the 25 SDK cases that need `s3fs`;
  - the 2 modules that cannot be collected.
- **The 240 test modules outside the suite** (#331 added three) give 2,265 passed, 80 skipped, 13 failed and 21
  collection errors. The failures are the same as round #145's. The 24 extra passes are the three new modules.
- **The doc audit**, run alone, finds one new unresolved reference: finding 103's villa main `deb1b6953`, from 11-03.
  - This checkout's villa clone stops at 10-16, and the audit never fetches, so it cannot resolve the commit here.
  - The 59 standing entries are of the same kind: commits of other repositories that the local clones do not hold.
  - The reference is the owner's record of villa's main that day, so it is left as written.
