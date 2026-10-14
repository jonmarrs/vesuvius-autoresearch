# Design and architecture review — what the loop's promotion commit records

Date: 2026-10-14. Baseline: `1f192218` (main after #69). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the git commit `run_autoresearch_loop.py` makes when a cycle is promoted. That commit is the history of the
incumbent: every `best_model.pt` the loop has kept, with the config that produced it.

## What changed

- **A promotion commits exactly its own files**: `config.json`, `best_model.pt` and `autoresearch_history.json`.
  `commit_promotion` runs `git add` and then `git commit --only`, which takes just those paths and leaves anything
  else in the index as it was.
- **`reports/figures/` is no longer part of the commit.** The loop does not write it.
- **A failed commit is recorded.** git runs without a shell, its exit is checked, and a failure is printed and
  written to the sprint log: `- **Commit**: failed (<reason>); best_model.pt and config.json are promoted on disk
  but not in git`.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **Promotion commits swept in whatever else was staged, and figures the loop does not write.** The commit was `os.system('git add config.json reports/figures/ best_model.pt autoresearch_history.json && git commit -m ...')`. A plain `git commit` records the whole index. On 2026-04-25, with this same command, `9dc5a419` ("NIGHT SHIFT: aug_mode_batchgeneratorsv2 improved model …") carried a 248-line `vesuvius_loader.py` change that had been staged. 35 of the 50 promotion commits carry `reports/figures/` files, which some other tool regenerated; the loop writes none. A code change filed under a promotion message is hard to find, and reverting the promotion reverts it too. Reproduced in a scratch repository: the old command commits a staged `work.py` and a changed `reports/figures/plot.svg` along with the loop's three files. | `commit_promotion` commits `PROMOTION_FILES` with `git commit --only -- <files>`. Test, in a real repository: with `work.py` staged and a figure changed, the commit holds only the three files, and `work.py` is still staged afterwards. |
| P3 | **A failed commit went unnoticed.** `os.system`'s status was ignored. A promotion that could not be committed left `best_model.pt` and `config.json` changed on disk but not in git, for example because of a lock file, a hook, or a missing identity. `git checkout -- .`, `git stash` or a pull could then undo it, and nothing said so. | The exit of each git step is checked. A failure is printed and written to the sprint log. Tests: outside a repository the commit reports `git add` failing; a failed commit is written to the sprint log. |

## Observations for the owner (not changed)

- **The commit runs the repository's pre-commit hooks** on the three files. None of them blocks it:
  - `check-added-large-files` checks only newly added files, and `best_model.pt` is already tracked;
  - the text hooks skip the binary checkpoint;
  - `config.json` and `autoresearch_history.json` are excluded;
  - mypy and the document guards run only for `.py` and `.md` files.

  A hook added later that fails would now be logged, not silently ignored.
- **`recent_configs.json` is tracked but not committed by the loop.** It changes every cycle (see the bandit-state
  review), and committing it would add a commit per cycle.
- **The 50 promotion commits stay as they are.** The 11 earliest (March and April) also carry sprint logs and
  `train.py` changes, from earlier versions of the loop.

## Reviewed and sound

- **The commit message** is built from the shift, the tweak name and `val_f1`. It is now passed to git as an
  argument, without a shell, so no value can break the command.
- **The commit happens after the incumbent is settled** (`settle_incumbent`, 2026-10-14), so it records the
  promoted model and never the hold.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #69's head, whose tree is `1f192218`'s.

- Baseline: 42 failed, 2124 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2126 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- a promotion commits only the loop's files (a real git repository with staged work and a changed figure);
- a failed promotion commit is recorded (`git add` failing outside a repository; a failed commit in the sprint
  log).

The loop tests' stubs moved from `os.system` to `commit_promotion`, including the lifecycle test that a failed cycle
attempts no commit.

Not verified here: a commit on the GPU host, with its installed hooks.
