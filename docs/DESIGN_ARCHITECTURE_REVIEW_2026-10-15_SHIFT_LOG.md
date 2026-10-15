# Design and architecture review — one sprint log per shift

Date: 2026-10-15. Baseline: `fede4537` (main after #83). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- what reads protocol v3's patch counts (#66);
- the spawned loader workers (#74) against the scripts that patch the trainer, and their output;
- the watchdog and launchers against the start refusals added today (#81, #82, #83);
- the loop's shift bookkeeping: when a shift ends, and which sprint log a start writes to.

## What changed

- **A restart within a shift goes on with the shift's sprint log.** The loop resumes the log its pointer
  (`.current_day_shift_log`) names when that log is this shift's: the same shift, begun the same day, as its name
  records (`sprint_log_<started>_<shift>.md`). A night shift past midnight began the evening before
  (`shift_began`). Only a log in `sprint_logs/`, with a valid date, started within its shift's hours, is resumed.
- **A resumed log gets a "Resumed at" line**, which says that cycle numbers start again from 1. It is written once
  however many restarts follow without a cycle.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **Every restart within a shift began a new sprint log.** At start, the loop meant to resume the shift's log if the pointer named one. The check looked for `shift_name.lower()`, "day shift", in a name spelled `day_shift`, so it never matched. Any restart then began a new file with a new header: a crash restarted by the watchdog, or a `stop.sh` and `start.sh`. Behind that, the date check would also have split a night log at midnight: it compared that day's date with the evening's log. The shift's record ended up across several files. One day shift of 2026-07-06 in `sprint_logs/` left three logs: 07:20, 15:49 and 16:20. | `shift_log_to_resume` matches the shift by its name and the day by when the shift began. Tests: two starts in one shift write one log, with one header, both starts' cycles, and the "Resumed at" line between them (fails on main). For night shifts across midnight, other nights, the other shift, and a missing file or another name, the helper resumes exactly the shift's own log (new helper). |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| A restart that runs no cycle added a "Resumed at" line on each start. With nothing under the VRAM cap the loop ends at once, which the code keeps out of the sprint log for this reason. The watchdog restarts it every few minutes, so this came to about 140 lines a shift. Not a regression: each start used to add a whole new log. | The marker is not written again while it is the log's last line. Test: three such restarts leave one marker (three on the first head). |
| The shift is decided by `time.localtime()` and the log named by `datetime.now()`, read a moment apart. A start at 06:59:59.99 could name a night log 07:00:00, which that evening's shift would then resume. | A log is resumed only if it was started within its shift's hours. Tested. |
| A pointer naming an impossible date (`2026-02-30`) raised in `main()` at every start; one naming a path outside `sprint_logs/` was resumed. Only a hand-edited pointer does either. | Neither is resumed. Tested. |
| The test of two starts read the real clock, and could fail when its two runs straddled 07:00. | The tests fix the loop's clock at noon. |
| The doc said the night log "was split" at midnight (the name check failing first hid that), that cycle 5's figure is "now" also overwritten by resumed runs (every restart already did), that `train.py`'s top level only prints, and that the watchdog discards `status`'s output (only its own check does). | Corrected. |

## Observations for the owner (not changed)

- **The resumed log numbers cycles from 1 again.** The cycle counter also decides when the loop checks before a
  cycle (from cycle 2 on) and when the every-fifth-cycle benchmark runs, so it is not carried over. The
  "Resumed at" line says so.
- **The benchmark's figure is named by cycle number** (`reports/benchmark_v210_cycle<N>.png`). Every shift, and every
  restart, writes cycle 5's figure over the previous one; that was so before this change.
- **`./start.sh` beside an orphaned run** prints the run (from `status`) and then "Autoresearch launcher started".
  The loop it launched then refuses, which is written to `autoresearch.out`. The watchdog behaves the same way and
  logs to `watchdog.log`.
- **The pointer's name, `.current_day_shift_log`,** serves both shifts. It is not renamed, because a rename would
  lose the pointer a running checkout has.

## Reviewed and sound

- **Protocol v3's counts (#66).**
  - `usable_patches` now counts ink-containing patches and `empty_target_patches` the ink-free ones, under v2 and v3
    alike.
  - The noise probe's check that the two add up to the requested sample still holds, as do the re-score's
    "zero usable" refusal and the reports that read them.
- **The spawned loader workers (#74) against the trainer's patchers.**
  - `train_with_new_augs.py` patches `apply_scroll_specific_3d_augmentations`, which the training step calls in the
    main process. `run_noise_probe.py` patches the skeleton-histogram directory, which validation uses in the main
    process.
  - Nothing patches the loader or its datasets, which are what run in the workers.
  - Every script that drives `train()` keeps its work under `if __name__ == "__main__"`, so a spawned worker that
    re-imports it does not run it (checked by AST).
  - `train.py`'s own top level runs no training. It imports, patches `kimimaro` and `wandb`, sets `stdout` to line
    buffering, and prints its two `DEBUG:` import lines, which each worker therefore prints too.
- **The workers' messages reach the log.**
  - A worker registers `os._exit` at exit, so a buffered `stdout` might have been lost. A test run with two workers
    and the training process stopping mid-pass found the workers' lines in a redirected log, with and without
    `PYTHONUNBUFFERED`.
  - Multiprocessing flushes a child's streams before its exit handlers run. `train.py` also line-buffers
    `stdout`, and the loop's runs are unbuffered anyway.
- **The workers' randomness.** Each patch's crop comes from a generator seeded by its index and the run's seed, so
  which worker prepares a batch does not change it.
- **The watchdog and launchers against today's refusals.**
  - `status` lists unsupervised runs, but its exit code still reports only the lock holder.
  - The watchdog's own check discards its output. The `start.sh --watchdog` it then runs writes it to
    `watchdog.log`, and `start.sh` by hand shows it.
  - The loop's start refuses beside such a run, and the next tick tries again.
- **When a shift ends.** The loop ends a shift once the hour leaves its bucket (07:00–19:00 for the day), so a cycle
  that runs through the boundary cannot carry the shift into the next one.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of #83's head, whose tree is `fede4537`'s but for one line of a review doc. It was
  42 failed, 2183 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are environmental: no scroll
  data, no CUDA, no villa data files.
- Branch, first head: 42 failed, 2185 passed, 15 skipped, 1 xfailed, 2 errors.
- Branch, after the PR review's fixes: REVIEW_RESULT
- Ruff (check and format) and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- `test_a_restart_within_the_shift_goes_on_with_its_sprint_log` (fails on main);
- `test_restarts_that_run_no_cycle_mark_the_log_once` (fails on the first head);
- `test_a_night_shift_past_midnight_is_the_evening_s_shift` (new helper).

Not verified here: a restart on the GPU host across midnight.
