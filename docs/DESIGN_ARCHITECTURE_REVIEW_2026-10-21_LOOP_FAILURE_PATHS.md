# Design and architecture review — every test with the locked packages, and the loop's untested failure paths

Date: 2026-10-21. Baseline: `da216ea6` (main after #178).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: two things #178 made possible.
- With the four locked packages it measured, every test in `tests/` can run here, not only the standard suite's.
  Earlier rounds checked the out-of-suite tests without them (#155, #166).
- With coverage, the standard suite shows which lines of the loop's core files no test runs:
  - `run_autoresearch_loop.py`;
  - `scripts/training/promotion.py`, `config.py` and `train.py`;
  - `src/vesuvius_autoresearch/core/vesuvius_loader.py`.

  coverage.py 7.6.12 was installed outside the venv for this.

Main has not moved since #178. There are no open pull requests. This round covers the 19:12 and 20:13 UTC firings.

## What changed

- **The loop's failure paths had no test.**
  - The standard suite runs 87% of `run_autoresearch_loop.py`. Among the lines it missed are three ways a cycle
    fails, each of which decides what the sprint log records and what happens to the incumbent.
  - **A clean exit whose `run_result.json` cannot be read** (lines 1270–1273). The cycle is recorded as a crash. A
    model the run had already promoted is moved aside, the incumbent is put back, and the run's rows are removed
    from `results.tsv` and `prize_readiness.tsv`.
  - **A preflight that times out** (lines 1167–1169 and 1174). It is named "preflight timed out after 300 s". `run.log`
    gets "PREFLIGHT TIMED OUT", and the sprint log's last log line is the preflight's own, not the loop's markers.
  - **A run that cannot be started** (lines 1208–1209), for example `uv` missing. It is named
    "could not be run (FileNotFoundError: …)".
- **Two of `promotion.py`'s refusals had no test:**
  - an incumbent that torch loads but that is not a checkpoint dictionary (line 199);
  - an older incumbent whose first-use record of its validation inputs cannot be written (lines 282–283).

  Both raise `IncumbentUnavailable` rather than let a candidate replace an incumbent that cannot be compared.
- **Tests** (`tests/test_autoresearch_measurement.py`, +5, in the standard suite):
  - **Three drive the loop** through `_drive_loop`, which gains an optional `preflight` callable so a preflight can
    time out or fail to start.
    - The unreadable-result case checks:
      - the incumbent restored and the promoted model kept aside;
      - the config unchanged and the rows removed;
      - the family weights not decayed.
    - The timeout case checks both markers in `run.log`, the named failure, the preflight's last line, the incumbent
      untouched and no decay.
    - The start-failure case checks the named failure and the incumbent untouched.
  - **Two test the refusals.**
    - A bare tensor saved as `best_model.pt` blocks promotion, through `train.promotion_decision`.
    - A directory at the first-use record's path stops `promotion.check_incumbent`.
  - The timeout test also checks that the preflight is given the 300 s its failure names. That message is a separate
    string from the `timeout=300` it describes.
  - Each of these mutants fails at least one of them:
    - an unreadable result not marked a crash;
    - the preflight timeout not caught;
    - the timeout marker dropped;
    - the last log line read after the loop's markers;
    - a start failure left unnamed;
    - a crash decaying the families;
    - the dictionary check dropped;
    - the record's `OSError` not caught;
    - the preflight's timeout changed from 300 s.

## Verified, no change needed

- **Every test in `tests/`, with the four locked packages ahead of the venv's own:** 4385 passed, 98 skipped and
  1 xfailed. There were 20 failures and 19 errors, all from what this container lacks:

  | cause | failures | errors |
  |---|---:|---:|
  | villa files absent from the sparse checkout: `vc_proofreader`, `volume-registration`, `multi-task-3d-unet` | 10 | |
  | villa's spiral modules absent (the probe tests' collection) | | 19 |
  | `local_data/` spiral patches absent (gitignored) | 5 | |
  | a local LeJEPA pretrain checkpoint absent | 1 | |
  | the owner's `spiral_out` fits absent (`correlate_geometry_ink.py`) | 1 | |
  | `villa/.git` a directory here, not a submodule's gitlink file | 2 | |
  | the doc guard on `villa/` paths and the gitignored detector checkpoint | 1 | |

  So none of the failures and errors is a failure of this repository's code, with one caveat. The doc guard's list
  includes `villa/ink-detection`, cited in `reports/villa_component_coverage.md`. The guard's own exemption for
  `METHOD.md` says villa moved that directory to `deprecated/`, so that path may be stale even with all of villa
  present. That cannot be checked without villa.
- **No test changes a tracked file.** `git status` is clean after the whole directory has run.
- **Coverage, before and after these tests:**
  - `run_autoresearch_loop.py` goes from 87% to 89%: exactly the ten targeted lines are gone.
  - `promotion.py` goes from 98% to 100%.
  - `config.py` stays at 99%. Its one missed line is the old `uri` fallback, `uris = [uri]` when `uri` is set and
    `uris` is not.
  - `vesuvius_loader.py` stays at 87%.
  - `train.py` is at 60%. Most of what the suite does not run is `train()`'s loop over real data, which the smoke
    preflight and the loop's own cycles exercise instead.

## Observations for the owner (not changed)

- **The loop's remaining untested lines** are mostly messages. Among them:
  - the night shift's end-of-sprint text;
  - the VRAM cap's exclusion note;
  - the rotation of `run.log` past 10 MB;
  - the every-fifth-cycle benchmark's three failure messages.

  None of those changes what is promoted. Two untested paths do touch the incumbent:
  - `settle_incumbent` when the hold link has vanished during the cycle (lines 618–619): it warns and leaves the
    run's model in place;
  - a promotion row that cannot be restored (lines 600–602).
- **The unreadable-result path writes no last log line.** The sprint log's entry for it gives the named failure but
  not the run's last line, since that path does not read it. Whether it should is the owner's call.
- **The out-of-suite tests that need the owner's data fail here rather than skip**, as their tests intend
  (`test_patches_are_present`). They can only be checked on the owner's machine.

## Verification

- `pytest tests/test_autoresearch_measurement.py` on the new tests and their neighbours: they pass, and the mutants
  above each fail one.
- **The standard suite with the locked packages** (as in #178): 2752 passed, 9 failed, 22 skipped and 1 xfailed. That
  is #178's 2747 plus the five new tests, with the same nine villa-file failures. The smoke test gave 9 of 11 passed
  and 2 skipped, as on main.
- Ruff 0.9.10 `check` and `format` are clean on the test file, which was formatted before.
- **Independent review** of the first two commits, in a worktree without villa. It found nothing blocking.
  - It confirmed:
    - every listed mutant fails a new test, from 20 of its own;
    - the stubs match how the loop calls `supervisor.run` and how `ProcessSupervisor.run` raises;
    - the `preflight` hook cannot change an existing test;
    - from the code, the unreadable-result path restores the incumbent and rows and decays nothing;
    - the coverage figures and the failure table.
  - Its should-fix finding: this document named the wrong missed line of `config.py`.
  - Its nits:
    - the preflight's timeout was not pinned;
    - the line ranges;
    - the coverage after the change;
    - which tests call what;
    - the `villa/ink-detection` caveat;
    - the two untested paths that touch the incumbent;
    - the missing last log line.

  All are addressed above.
