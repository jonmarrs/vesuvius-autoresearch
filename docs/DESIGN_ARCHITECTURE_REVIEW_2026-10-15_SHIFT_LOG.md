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
  (`shift_began`). A resumed log gets a "Resumed at" line, which says that cycle numbers start again from 1.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **Every restart within a shift began a new sprint log.** At start, the loop meant to resume the shift's log if the pointer named one. The check looked for `shift_name.lower()`, "day shift", in a name spelled `day_shift`, so it never matched. Any restart then began a new file with a new header: a crash restarted by the watchdog, or a `stop.sh` and `start.sh`. The night log was split again at midnight, since its date check compared that day's date with the evening's log. The shift's record ended up across several files. One day shift of 2026-07-06 in `sprint_logs/` left three logs: 07:20, 15:49 and 16:20. | `shift_log_to_resume` matches the shift by its name and the day by when the shift began. Tests: two starts in one shift write one log, with one header, both starts' cycles, and the "Resumed at" line between them (fails on main). For night shifts across midnight, other nights, the other shift, and a missing file or another name, the helper resumes exactly the shift's own log. |

## Observations for the owner (not changed)

- **The resumed log numbers cycles from 1 again.** The cycle counter also decides when the loop checks before a
  cycle (from cycle 2 on) and when the every-fifth-cycle benchmark runs, so it is not carried over. The
  "Resumed at" line says so.
- **The benchmark's figure is named by cycle number** (`reports/benchmark_v210_cycle<N>.png`). Every shift, and now
  every resumed run, writes cycle 5's figure over the previous one.
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
  - `train.py`'s own top level only sets `stdout` to line buffering and prints its two `DEBUG:` import lines,
    which each worker therefore prints too.
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
  - The watchdog discards its output. `start.sh` shows it.
  - The loop's start refuses beside such a run, and the next tick tries again.
- **When a shift ends.** The loop ends a shift once the hour leaves its bucket (07:00–19:00 for the day), so a cycle
  that runs through the boundary cannot carry the shift into the next one.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline (`fede4537`): VALIDATION_BASELINE
- Branch: VALIDATION_BRANCH
- Ruff (check and format) and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- `test_a_restart_within_the_shift_goes_on_with_its_sprint_log` (fails on main);
- `test_a_night_shift_past_midnight_is_the_evening_s_shift` (new helper; fails on main).

Not verified here: a restart on the GPU host across midnight.
