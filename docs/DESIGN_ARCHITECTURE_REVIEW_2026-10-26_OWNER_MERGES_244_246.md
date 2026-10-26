# Design and architecture review — the owner's #244 (replicate rule), #245 (cycles.jsonl) and #246 (its window test)

Date: 2026-10-26. Baseline: `31a43fd0` (main after the owner's #244, #246 and #245).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 18:13 UTC firing. The 12:33–17:13 firings found main unmoved after #243.
- **#244** replays a promotion rule over a tweak's replicates on the 546 cycles before the batchgeneratorsv2
  confirmation's window (`scripts/loop_replicate_rule.py`, `reports/loop_replicate_rule_2026-10-26.md`).
- **#246** registers that rule, frozen at c = 4.5, for a test on the confirmation window's cycles, with its power
  (`docs/preregistration/2026-10-26_loop_replicate_rule_window.md`).
- **#245** makes the loop append one JSON line per cycle to `cycles.jsonl`: its tweak, start, commit, working-tree
  changes to what a cycle runs, status and `run_result.json`. `train.py` now writes its step count.

## What changed

- **`cycles.jsonl` missed edits to part of the code a cycle runs.**
  - #245 records `git status` for `LOOP_CODE_PATHS`, as "any working-tree change to what a cycle runs".
  - `train.py` also imports seven files of this repository from outside those paths:
    - the losses, `scripts/betti_loss_module.py` and `scripts/cldice_loss.py`;
    - `scripts/pixel_auc.py`, which computes the validation ROC AUC, one of the two measures the replicate rule
      reads;
    - the augmentations, `scroll_augmentations.py`;
    - the models, `vesuvius_model.py`;
    - the loader wrapper, `volume_cartographer_wrapper/`;
    - `scripts/wandb_tracking.py`.
  - An uncommitted edit to any of them ran in the cycle, and the cycle was recorded as running the commit unchanged.
  - They are now in `LOOP_CODE_PATHS`.
  - A new test in `tests/test_loop_lifecycle.py` follows the imports of `train.py` and of the loop through this
    repository's files: imports inside functions count, relative ones too, and villa is left out. It requires every
    file it reaches to be covered, and every listed path to exist. Against #245's list it fails, naming the seven.
  - The empty `scripts/__init__.py` is not listed. The suite guard
    (`tests/test_validation_suite_covers_the_loop.py`) counts a package marker with no code as no code. Listing it
    made the loop name a file the guard reads as a script named but not run. The coverage test follows the same
    rule, so a marker that gains code must be listed.
  - On this checkout, `code_state()` with the longer list takes 0.17 s and reports the edited loop file.

## Verified, no change needed

- **#244's and #246's records regenerate byte for byte** from `reports/loop_tweak_replication_2026-10-25.json`.
  The owner's tests bind the report's and the registration's figures to them.
- **The record reads no window cycle.** Its starts are all `YYYY-MM-DDTHH:MM:SS`, so the string comparison with the
  window's start orders them correctly. The last starts at 2026-10-25 14:10:57.
- **The window test reads the confirmation's output as `scripts/loop_tweak_replication.py` writes it.**
  - The verdict's status is `OK`, `INCOMPLETE` or `UNMATCHED_RUNS`, and the last two carry no reading. The reading is
    `CONFIRMED`, `F1_ONLY` or `NOT_REPLICATED`.
  - The registered keys it compares (window start, standing tweak, the cut at the 8th cycle, at least 6 standing
    cycles and 60 others) are that script's `REGISTERED`.
  - The confirmation's rows carry start, epoch, tweak and val_f1, with the matched run's ROC AUC. An unmatched row
    makes the status `UNMATCHED_RUNS`, so the rule never reads a row without AUC.
  - It cuts the rows where the confirmation's verdict does: after the 8th standing cycle.
- **#246 was registered before the window's analysis.** Its commit is from 08:26 PDT, as "about 08:30" says. The two
  `history.tsv` rows it mentions are disclosed in #244's description.
- **#245's record is written where it should be.**
  - It is appended after the cycle's sprint-log entry, inside the span where a stop waits. A record that cannot be
    written is printed and does not stop the loop.
  - A crashed cycle records `result: null`.
  - `_run_git` returns stderr and stdout together. `code_state()` takes the last line of `rev-parse` and only lines
    in `git status --porcelain`'s shape, so a git warning does not enter the record.
  - `--no-optional-locks` leaves no `index.lock` behind. Untracked files inside villa are not reported.
- **`steps` is the training loop's counter**: set to 0 once and incremented once per step (the owner's AST test).

## Observations for the owner (not changed)

- **Pulling this change or #245 into the loop's checkout during the window.**
  - The confirmation's registration puts an epoch boundary at "a merge into the loop's checkout [that] changes what
    it runs".
  - Neither change alters training, scoring or the choice of tweak; both change what the loop writes about a cycle.
    Whether such a merge counts is the owner's call under that registration.
  - The replicate rule's power assumes one epoch.
- **`started` and `logged` are local times without an offset**, as the sprint logs and the registered windows are.
  When PDT ends on 2026-11-01, 01:00–02:00 repeats, and sorting by `started` would interleave those cycles. The
  file's line order is the cycles' order.

## Verification

- **#244–#246's tests** (`tests/test_loop_replicate_rule.py`, `tests/test_loop_lifecycle.py`,
  `tests/test_autoresearch_measurement.py`, `tests/test_loop_tweak_replication.py`) gave 206 passed on main.
- **The new coverage test** passes with the change and fails against #245's list.
- **The guard set:** the doc guards, the withdrawn-claims ledger, the suite guard, and the filing, form,
  rollover, villa-draft, loop-tweak, replicate-rule, lifecycle and measurement tests.
  - With the change it gives 575 passed and 6 skipped.
  - The one failure is the standing `test_live_documents_stay_clean`, which lists villa paths absent from this
    container's villa checkout. Its list is the same as on main.
- **Ruff** 0.9.10 `check` and `format`, and **mypy** with the hook's flags, are clean on the two changed Python
  files.
- **Doc audit:** main's run differs from #243's only in three more cited paths, all present. This record adds no
  entries.
- **No independent review this round.** The change is one tuple and its test.
