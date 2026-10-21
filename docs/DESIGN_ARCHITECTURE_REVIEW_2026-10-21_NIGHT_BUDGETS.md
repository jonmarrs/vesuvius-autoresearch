# Design and architecture review — the night budget after #159, and finding 94's rescoring

Date: 2026-10-21. Baseline: `e9b6a799` (main after #164).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- **The owner's #159**: 15-minute cycles at night as by day (`SHIFT_BUDGETS`, `shift_for_hour`,
  `LONGEST_RUN_SECONDS`), and what else assumed a 3600-second night.
- **The owner's #162**: finding 94, `scripts/tolerance4_rescore.py`, its report and tests, checked against
  `docs/preregistration/2026-10-20_tolerance4_rescore.md`.
- The filing draft's edits in #160 and #164, lightly.

No owner PR is open.

## What changed

- **The epoch-boundary overhead measure took a night cycle's budget from the shift.**
  - `epoch_boundary_overhead.cycles` set every night-shift log's budget to 3600 s. Since #159 a night cycle runs
    900 s, so its overhead would read about 2580 s below zero. `cycle_length_gain.py` reads its cycles from the same
    function.
  - The shift was not a safe source before #159 either: the night logs recorded 900 s until early May 2026.
  - **Change:** a cycle's budget is now the `time_budget` its own config line records. The loop writes that line
    from the run's config, `asdict(config)`, every cycle. A log too old to record one (before 2026-04-14) keeps its
    shift's 3600 s or 900 s, as before.
  - For the October logs `cycle_length_gain.py` reads, the recorded budgets are the ones the file name gave, so its
    results do not move.
- **The loop's preflight message said "skipping 60-min run"** whatever the budget. It now gives the cycle's own
  minutes, as the loop's other messages do.
- **The sprint's end kept its own copy of the shift's hours.** #159 put them in `shift_for_hour`, which `main()` uses
  to start a shift. The check that ends the sprint once the hour leaves that shift still tested `7 <= hour < 19`
  itself. It now asks `shift_for_hour`, so the two cannot drift apart. For every hour and both shifts it gives the
  same answer as before.
- **`METHOD.md` and `docs/RESEARCH_PAPER.md` still gave 60-minute nights.**
  - `METHOD.md`'s step 3 now gives 15 minutes in both shifts, with the date nights changed.
  - The paper's status line says it tracks the loop's current state. Its two budget statements now give the same,
    dated.
  - Its introduction also said the loop promotes on `val_bpb`. It now says `val_f1`, gated by AP-prevalence lift,
    with `val_bpb` until 2026-07-11, as `METHOD.md` records.
- **Tests:**
  - `tests/test_epoch_boundary_overhead.py`:
    - a night log of 2026-10-20 that restarts from 3600-second cycles onto 900-second ones; each cycle is measured
      against its own budget;
    - logs with no recorded budget keep their shift's.

    Each of these mutants is killed: the budget from the file name only; the fallback always 900; the budget read
    from the whole log, not the cycle's block.
  - `tests/test_tolerance4_rescore.py` now runs `main()` end to end, with ScrollGT's scorer and target stubbed. It
    checks four things:
    - each labelling is scored at tolerance 4 against its cube's own target, and checked against its own published
      row (our tracer's and connected components' differ in the stub);
    - our tracer's labellings come from finding 80's and finding 83's directories, by group;
    - one labelling with an extra instance gives `IDENTITY_FAILED` with no verdict, and exit code 1;
    - another scoring version is refused.

    Each of these mutants is killed:
    - every labelling checked against our tracer's row;
    - the scoring tolerance at 2;
    - every labelling read from one directory;
    - the neural tracer's tolerance-2 rows used for its tolerance-4 ones;
    - the identity check or the version check skipped;
    - connected components' published rows written as ours;
    - connected components taken of the skeleton, not the mask;
    - exit code 0 whatever the status.
  - `tests/test_shift_budgets.py`: the sprint's end is decided by `shift_for_hour`, and the old copy of the hours is
    gone (a check of `main()`'s source, as the file's other test of `main()` is).
  - `tests/test_tolerance4_rescore_report.py` pins two more things:
    - every row's tolerance (4 for the rescored and neural rows, 2 for the published ones) and scoring version (3);
    - that the neural tracer's tolerance-4 rows keep its published rows' fixed fields, as ours do.

    The report's five offset cubes were a literal in the test. They are now checked against
    `neural_tracer_gt_offset.json`: the cubes whose mean shift is at least a voxel long.

## Verified, no change needed

- **#159's loop change.**
  - `shift_for_hour` gives the day shift from 07:00 to 19:00 and the night otherwise, each 900 s.
  - `main()` takes its shift and budget from it at start, and ends the sprint when the hour leaves that shift, as
    before #159.
  - `config.py`'s `time_budget` default (3600) stays. The loop overrides it every cycle, and only a direct run uses
    it, as #159 says.
- **#162 against its registration.**
  - **Unchanged since registration:** the script and its test were committed with the registration (`04cb7e51`,
    11:23 PDT) and are unchanged on main. The run is recorded as 11:24–12:20; the result was committed at 12:25.
  - **Data:** our tracer's labellings are read from finding 80's directory for the 11 in-sample cubes and finding
    83's for the 10 held out. Connected components are ScrollGT's own of each cube's mask. The neural tracer's rows
    are `descriptive_tolerance_4` from finding 91, not re-run.
  - **Identity:** all 42 labellings reproduce their published rows' instance count, predicted and ground-truth
    length, and ground-truth fibers, exactly. The neural tracer's 21 tolerance-4 rows also match its published
    rows on those fields. Every rescored row records tolerance 4 and scoring version 3, and every published row
    tolerance 2.
  - **Verdict:** P1 needs the neural tracer above ours on at least 6 of 8 Scroll-3 cubes, and P2 below ours on at
    least 9 of 11 in-sample cubes, strictly, so a tie counts as neither. The JSON gives 8 of 8 and 8 of 11: P1 held
    and P2 failed. The readings are the registered sentences.
  - **The report's figures:** its tests recompute each from the JSON. These are:
    - the group medians;
    - the Scroll-3 ratio, 2.22 (1.87–2.79) against 1.26;
    - the in-sample ratio, 0.71 against 0.36;
    - the three 512³ cubes, 49.50 against 43.69;
    - the gains with tolerance.
  - **The two of three:** of the three in-sample 512³ cubes, `s5_06494_01994_03994` and `s5_06994_00994_04994` are
    among the five offset cubes; `s5_07994_01994_05494` (a shift of 0.21 voxels) is not.
- **The filing draft (#160, #164).**
  - Its finding-94 bullet, its 0.8.2 entry and its failed-prediction tally (now 22) agree with the report.
  - `tests/test_filing_2026_10_numbers.py` binds each, and passes here. Its four tests that need the sibling
    checkouts skip, among them the one that ties the cite to ScrollGT's newest tag. So that `v0.8.2` exists and
    carries the tolerance note is not checked here.

## Observations for the owner (not changed)

- **`LONGEST_RUN_SECONDS` is now 1200 s, from 3900.**
  - The loop uses it for one thing: a run that a loop or the ablation started and that has outlived its supervisor
    is stopped once older than this.
  - Two kinds of run now meet it before their own timeout:
    - an orphaned 3600-second night run left by a loop started before #159;
    - an orphaned ablation cell run with `--budget` above 960 s (its timeout is the budget plus 240 s).

    Its comment calls it the longest a supervised run may last, which the ablation's `--budget` does not bound.
  - Neither run has a supervisor left to record it, and stopping it keeps it from replacing `best_model.pt` or
    `run_result.json`. Before #159 the loop left such a run going, and refused to start on every watchdog tick, until
    the run ended or passed 3900 s.
  - Whether the limit should follow the ablation's budgets too is the owner's call.
- **The registration's `INCOMPLETE` path is unreachable from `main()`.** A missing labelling stops the run before
  any JSON is written; it is not counted as unscored. The committed run scored all 21 cubes, so the result is
  unaffected. `verdict()` handles unscored cubes as registered, and its tests cover it.

## Verification

- `pytest` on `test_epoch_boundary_overhead`, `test_cycle_length_gain*`, `test_shift_budgets`,
  `test_tolerance4_rescore*` and `test_filing_2026_10_numbers`: 91 passed, and the filing test's 4 skipped for want
  of the sibling checkouts.
- Ruff, ruff format and mypy are clean on the changed files.
- The standard suite, the smoke test and the independent review are recorded below once run.
