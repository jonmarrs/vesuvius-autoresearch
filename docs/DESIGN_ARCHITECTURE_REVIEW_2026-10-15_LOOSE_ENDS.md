# Design and architecture review — loose ends of stopping and saving

Date: 2026-10-15. Baseline: `c9dee3e6` (main after #78). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what the stop and state reviews of 2026-10-14 and 2026-10-15 (#69, #73, #76, #77, #78) left open:
- how the commands that run supervised work or hold the lock take a stop: the noise probe, the augmentation
  ablation, the incumbent re-score, and `scripts/iterative_pseudo_labeling.py --execute`, which did not take one;
- the loop's per-cycle state files and how they are written (`autoresearch_history.json`, `recent_configs.json`,
  `config.json`);
- what the README tells an operator about the lock.

## What changed

- **One guard, `process_supervisor.stops_interrupt()`, makes SIGTERM and SIGHUP interrupt supervised work**, as
  Ctrl-C does. The noise probe, the ablation, the re-score and now `iterative_pseudo_labeling.py --execute` use it
  in place of their own SIGTERM handlers.
  - The supervisor stops the child's group, and the caller's clean-up runs: its lock is released, its staging
    directory removed.
  - A signal the process ignores, such as nohup's SIGHUP, stays ignored. Outside the main thread, where Python
    cannot install handlers, the guard does nothing.
  - The previous handlers are restored, with `SIG_DFL` for one not set from Python.
- **The pseudo-labeler exits with 130** ("pseudo-label preparation interrupted") on an interrupt, not a traceback.
- **`recent_configs.json` is written atomically**, through the same temporary-file-and-rename helper as the family
  weights (`_write_json_atomic`, factored out of `save_history`). The helper keeps the file's mode (`mkstemp`
  creates 0600) and syncs the file before the rename.
- **`.gitignore` covers the atomic writers' temporaries** (`.*.tmp`), left only by a SIGKILL mid-write.
- **The README names the work that holds the lock** (the noise probe, the ablation and the re-score), and says that
  `stop.sh` stops whichever does.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A kill left the pseudo-labeler's generator running.** With `--execute` it runs each region's generator under `ProcessSupervisor`, in a session of its own, with a one-hour timeout by default. With no handler, a SIGTERM ended the command at once: no `finally` ran. The generator went on, on the GPU when `--device` is one, writing into a staging directory (`.<out>-*`) that nothing would publish or remove. Ctrl-C was already handled: it reaches the command as `KeyboardInterrupt`, and an existing test shows the staging is then removed. | SIGTERM and SIGHUP interrupt it while `--execute` runs (`stops_interrupt`). Tests: with the real supervisor and a real generator that has a child of its own, a SIGTERM or a SIGHUP ends the whole group, nothing is published, no staging directory is left, the command exits 130, and the handlers are restored. On main the signal reaches its default action (the test catches it rather than letting it end the run). |
| P3 | **A closed terminal did the same to every lock holder.** SIGHUP (a dropped ssh session; `uv run` passes it on) ended the noise probe, the ablation or the re-score at once. Their supervised trial or cell ran on, and their lock was released with it still at work, so the watchdog could start the loop beside it. Only SIGTERM was handled. | All of them use `stops_interrupt`, which covers SIGHUP unless it is ignored (`nohup`). Tests: SIGTERM and SIGHUP interrupt guarded work and the previous handlers return; an ignored SIGHUP stays ignored; in a thread the guard changes nothing. |
| P3 | **`recent_configs.json` was written in place.** The loop saves it each cycle as it picks a tweak, before the run. A stop or crash during the write left it cut short; the next start read it as unreadable, printed a warning and began with no recent configs, so the dedup that keeps the loop from retrying a config it just tried started over. The family weights beside it have been written atomically since 2026-10-14. | Written through `_write_json_atomic`. Test: a stop in the middle of the write leaves the previous file, which still loads, and no temporary file. Fails on main (the file is left cut short). |
| P3 | **The atomic writer narrowed the file's mode and did not sync.** `mkstemp` creates 0600, so the rename left `recent_configs.json` (tracked, 0644) readable by its owner only; the family weights have been 0600 since 2026-10-14. Without an fsync, a power loss could leave an empty file on filesystems that do not order the rename after the data. | The mode of the file being replaced is kept, and the data is synced before the rename. Test: a 0644 file stays 0644. Fails on the PR's first head. |
| — | **The README described the lock as the loop's.** Since #73 and #76 the ablation and the re-score hold it too, and each refuses to start beside the others. | One paragraph lists them. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| SIGHUP (a dropped ssh session) still left the generator running, and the one-hour timeout went with the parent. | Fixed for all four commands through `stops_interrupt`. Tested with a real generator and its child. |
| The pseudo-labeler test replaced the supervisor, so no generator, group or kill was exercised. | A second test runs a real generator with a child under the real supervisor and sends real signals. |
| An interrupt ended the command with a traceback. | Exit 130 with a message. |
| The handler install was unsafe off the main thread, with a handler not set from Python, or with SIGHUP ignored, and was repeated in four commands. | One guard handles each case; the four commands use it. |
| The writer narrowed the mode to 0600 and did not fsync. | Mode kept; synced. Tested. |
| A SIGKILL mid-write left `.…json.*.tmp` files showing in `git status`. | Ignored (`.*.tmp`). |
| The recent-configs test raised `KeyboardInterrupt`; the loop's handler raises `SystemExit` there. | `SystemExit`, which also cannot abort the test session. |
| "`prepare_round --execute`" mixed a function and a flag; the README did not say the ablation's `--dry-run` takes no lock. | Corrected. |
| A signal inside `Popen`, before the supervisor records the child. | Unchanged; recorded in the supervisor review. |

## Observations for the owner (not changed)

- **`config.json` itself is never written in place by the loop.** It is replaced by renaming `config_temp.json` over
  it. `ExperimentConfig.save` writes in place, so a stop during that write can leave `config_temp.json` cut short;
  the next cycle writes it afresh.
- **Other operator scripts launch children with plain `subprocess.run`.** A kill of the parent leaves the child
  running, and Ctrl-C reaches both. They are analyses and launchers that hold no lock, and none writes the loop's
  files.
- **GPU jobs outside the lock** (`scripts/training/launch_*.py`, analysis scripts) can still run beside the loop and
  compete for the GPU. A cycle that runs out of memory is counted as a crash and not rewarded; one that is slowed
  gets fewer steps from its fixed time budget. Keeping the host otherwise idle is the documented practice
  (`docs/REPEATABILITY_PROBE.md`).

## Reviewed and sound

- **The family weights** (`save_history`) keep their behaviour: written atomically, with a warning on an `OSError`.
  Only the temporary file's prefix changes (`.autoresearch_history.json.*`), and the test that checks none is left
  behind looks for the new name.
- **`load_recent_configs`** still returns an empty list, with a warning, for an unreadable file. With the write
  atomic and synced, it should meet one only if the file is damaged some other way.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #78's head, whose tree is `c9dee3e6`'s.

- Baseline: 42 failed, 2155 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, first head: 42 failed, 2157 passed, 15 skipped, 1 xfailed, 2 errors.
- Branch, after the PR review's fixes: 42 failed, 2163 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 8 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop, the supervisor and the four commands:
  clean.

New tests:
- `tests/test_pseudo_handoff_contracts.py`:
  - `test_a_kill_stops_the_generator_and_publishes_nothing` (fails on main);
  - `test_a_kill_or_hangup_ends_a_real_generator_and_its_children` (SIGTERM, SIGHUP; both fail on main, SIGHUP
    on the first head);
- `tests/test_loop_lifecycle.py`:
  - `test_a_stop_or_a_closed_terminal_interrupts_supervised_work` (SIGTERM, SIGHUP);
  - `test_an_ignored_hangup_stays_ignored_and_threads_change_nothing`;
- `tests/test_autoresearch_measurement.py`:
  - `test_a_stop_while_recent_configs_are_saved_leaves_the_previous_file` (fails on main);
  - `test_the_atomic_json_writer_keeps_the_files_mode` (fails on the first head).

Not verified here: a kill of the pseudo-labeler on the GPU host with a real generator.
