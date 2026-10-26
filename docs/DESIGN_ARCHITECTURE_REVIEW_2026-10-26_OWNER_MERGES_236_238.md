# Design and architecture review — the owner's #236 (October research filing) and #238 (loop tweaks by replicate)

Date: 2026-10-26. Baseline: `fafa522a` (main after the owner's #236 and #238).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12 UTC firing. The 23:12–02:12 firings found main unmoved after #239.
- **#236** adds an optional research answer for the October prize, a CPU reproduction of ScrollGT's 512³ scorer memory
  fix, and updates to the plan and filing draft.
- **#238** reports an exploratory analysis of the loop's cycles since the 10-17 promotion. `aug_mode_batchgeneratorsv2`
  beats the other tweaks on val_f1, ROC AUC and AP lift, and the single-cycle rule cannot promote it. #238 also
  registers a confirmation on cycles from 2026-10-25 16:00 PDT.

## What changed

- **The registered confirmation read only one run log.**
  - The registration's Window section joins cycles to the run logs "as in the exploratory report". That report read
    `run.log.old` and `run.log`.
  - The registered command passed only `--run-log run.log`. The loop renames `run.log` to `run.log.old` once it
    passes 10 MB, deleting any older `run.log.old` (`run_autoresearch_loop.py`).
  - A rotation during the four-day window would leave the cycles before it unmatched. The registered rule would then
    give UNMATCHED_RUNS and no reading.
  - A dated amendment 1 in `docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md` gives the command with both
    logs. It also says to copy `run.log.old` aside if a second rotation could delete the window's first runs.
  - The amendment changes no prediction, threshold, window or rule, and the script is unchanged, as the registration
    requires. It was written during the window, before any analysis of it; nothing from the window's cycles is in
    this repository.
  - `tests/test_loop_tweak_replication.py` checks that the loop rotates, that the exploratory record read both logs,
    and that the amended command reads both.
- **The research answer described the ERL example as "one deletion".**
  - Its figures, 35.39 → 41.46 at coverage 0.62 → 0.38, come from deleting all our tracer's instances under 400
    voxels, as the filing draft and the findings summary say.
  - The answer now says so, and `tests/test_october_research_form_answers.py` checks it against the draft's sentence.
- **The research answer did not call finding 99 exploratory.**
  - Its evidence paragraph says "the linked context studies were pre-registered", then cites finding 99, whose report
    is among the links. The plan says the answer gives finding 99 "its ... exploratory limits".
  - It now reads "Finding 99, exploratory and not pre-registered, identifies …". The test binds it, and checks the
    finding's JSON status.
- **#236's new test was not ruff clean.** `tests/test_october_research_form_answers.py` had a `zip()` without
  `strict=` (B905), and `ruff format` would rewrite it. Pre-commit would stop the next commit that touched it. It is
  now clean under the pinned ruff 0.9.10.

## Verified, no change needed

- **#238's registration came first.** It was committed at 15:01 PDT on 2026-10-25, before its 16:00 window. The
  script is unchanged since.
  - Merges since then (#236, #238 and this series' #239) touch none of the loop's code paths named in the script's
    `EPOCHS`.
  - So no epoch is owed to the list.
- **#238's figures are the record's.** The owner's tests recompute every effect, Holm p, summary and per-epoch figure
  from the committed rows. Checked here as well:
  - the 0.67% false-promotion rate and the SD of 0.0029 are the pooled noise probe's
    (`reports/noise_probe_v3_pooled_2026-10-17.md`);
  - 17 of the 26 tweaks' val_f1 effects lie within ±0.001;
  - P4's strict `>` against the bar is train.py's own promotion test (`val_f1 > best + F1_NOISE_TOLERANCE`).
- **#236's figures:**
  - the CPU reproduction's peak RSS values (1.06, 5.50, 0.57 and 2.57 GiB) are the evidence JSON's KiB figures;
  - its test binds the 2.57 GiB, the 7 GiB budget and the 15 exact fields;
  - the research answer's coverage factors and finding 100 figures are bound by its test.

## Observations for the owner (not changed)

- **An unmatched cycle after the window still voids it.**
  - `registered_verdict` cuts its rows at the 8th standing cycle, but takes `unmatched` from the tally of everything
    up to `--until`.
  - Run with `--until` at the deadline, an unmatched cycle after the cut would give UNMATCHED_RUNS, although it is
    outside the window.
  - The registration allows `--until` at "any earlier time after the 8th standing cycle ends". Ending it there avoids
    the case. The script may not change under the registration.
- **One doc-audit entry from #236.** The plan cites villa's main as a backticked 322cb0899, as #235's draft does. This
  repository's villa checkout is at the pin, so the audit cannot resolve it, and no test fails.
- **Not checkable here:**
  - ScrollGT PR #14 and the ScrollGT walkthrough, which are in another repository;
  - the plan's live-form and link checks;
  - the loop's run logs, and so the 546-cycle join and the absence of batchgeneratorsv2 fallback warnings.

## Verification

- **Tests:** #236 and #238's tests, with the filing, form-answer and suite-guard tests, gave 71 passed and 4 skipped
  before this change. After it:
  - the loop-tweak tests give 18 passed;
  - the research-answer tests give 6 passed.
- **Perturbations:** each of three edits fails a new test:
  - "one deletion" restored;
  - the exploratory label removed;
  - the amended command reverted to one log.
- **Ruff** 0.9.10 `check` and `format` are clean on both test files.
- **Doc guards, the withdrawn-claims ledger, the suite guard, and the filing, form-answer, research-answer,
  loop-tweak and villa-draft tests:** 524 passed and 6 skipped.
  - The one failure is `test_live_documents_stay_clean`, which lists villa paths absent from this container's villa
    checkout.
  - Its list is the same as on main.
- **Doc audit:** #236 adds the one entry above. #238 adds none, and neither does this branch.
- **No independent review this round.** The changes are an amendment to a command, two phrases and their bindings,
  each checked by perturbation.
