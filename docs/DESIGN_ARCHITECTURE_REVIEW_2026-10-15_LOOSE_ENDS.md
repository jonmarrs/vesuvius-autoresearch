# Design and architecture review — loose ends of stopping and saving

Date: 2026-10-15. Baseline: `c9dee3e6` (main after #78). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what the stop and state reviews of 2026-10-14 and 2026-10-15 (#69, #73, #76, #77, #78) left open:
- the one supervised command that did not handle a stop, `scripts/iterative_pseudo_labeling.py --execute`;
- the loop's per-cycle state files and how they are written (`autoresearch_history.json`, `recent_configs.json`,
  `config.json`);
- what the README tells an operator about the lock.

## What changed

- **`iterative_pseudo_labeling.py --execute` takes SIGTERM as an interrupt**, as the noise probe and the ablation do.
  The supervisor then stops the generator's group, and the staging directory is removed, as for Ctrl-C. The
  previous handler is restored afterwards.
- **`recent_configs.json` is written atomically**, through the same temporary-file-and-rename helper as the family
  weights (`_write_json_atomic`, factored out of `save_history`).
- **The README names the work that holds the lock** (the noise probe, the ablation and the re-score), and says that
  `stop.sh` stops whichever does.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A kill left the pseudo-labeler's generator running.** `prepare_round --execute` runs each region's generator under `ProcessSupervisor`, in a session of its own, with a one-hour timeout by default. With no handler, a SIGTERM ended the command at once: no `finally` ran. The generator went on, on the GPU when `--device` is one, writing into a staging directory (`.<out>-*`) that nothing would publish or remove. Ctrl-C was already handled: it reaches the command as `KeyboardInterrupt`, and an existing test shows the staging is then removed. | SIGTERM raises `KeyboardInterrupt` while `--execute` runs. Test: a SIGTERM delivered during a step propagates as an interrupt, nothing is published, no staging directory is left, and the handler is restored. On main the signal reaches its default action (the test catches it rather than letting it end the run). |
| P3 | **`recent_configs.json` was written in place.** The loop saves it each cycle as it picks a tweak, before the run. A stop or crash during the write left it cut short; the next start read it as unreadable, printed a warning and began with no recent configs, so the dedup that keeps the loop from retrying a config it just tried started over. The family weights beside it have been written atomically since 2026-10-14. | Written through `_write_json_atomic`. Test: a stop in the middle of the write leaves the previous file, which still loads, and no temporary file. Fails on main (the file is left cut short). |
| — | **The README described the lock as the loop's.** Since #73 and #76 the ablation and the re-score hold it too, and each refuses to start beside the others. | One paragraph lists them. |

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
- **`load_recent_configs`** still returns an empty list, with a warning, for an unreadable file. It now meets one
  only after a crash outside the write itself.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #78's head, whose tree is `c9dee3e6`'s.

- Baseline: 42 failed, 2155 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2157 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop and the pseudo-labeler: clean.

New tests (both fail on main):
- `tests/test_pseudo_handoff_contracts.py::test_a_kill_stops_the_generator_and_publishes_nothing`;
- `tests/test_autoresearch_measurement.py::test_a_stop_while_recent_configs_are_saved_leaves_the_previous_file`.

Not verified here: a kill of the pseudo-labeler on the GPU host with a real generator.
