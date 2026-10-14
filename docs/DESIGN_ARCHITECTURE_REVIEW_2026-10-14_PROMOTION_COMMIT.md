# Design and architecture review — what the loop's promotion commit records

Date: 2026-10-14. Baseline: `1f192218` (main after #69). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the git commit `run_autoresearch_loop.py` makes when a cycle is promoted. That commit is the history of the
incumbent: every `best_model.pt` the loop has kept, with the config that produced it.

## What changed

- **A promotion commits exactly its own files**: `config.json`, `best_model.pt` and `autoresearch_history.json`.
  `commit_promotion` runs `git add` and then `git commit --only`, which takes just those paths and leaves anything
  else in the index as it was. A failed commit unstages the three files again.
- **`reports/figures/` is no longer part of the commit.** The loop does not write it.
- **A failed commit is recorded.** git runs without a shell, its exit is checked, and a failure is printed and
  written into the cycle's own sprint-log entry: `- **Commit**: failed (<reason>); config.json, best_model.pt and
  autoresearch_history.json are promoted on disk but not committed`. The reason is git's own: its `fatal:` and
  `error:` lines and failed hooks.
- **A hung git is stopped with SIGTERM**, on which git removes its lock files, after 300 s.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **Promotion commits swept in whatever else was staged, and figures the loop does not write.** The commit was `os.system('git add config.json reports/figures/ best_model.pt autoresearch_history.json && git commit -m ...')`. A plain `git commit` records the whole index. On 2026-04-25, with this same command, `9dc5a419` ("NIGHT SHIFT: aug_mode_batchgeneratorsv2 improved model …") carried a 248-line `vesuvius_loader.py` change that had been staged. 35 of the 50 promotion commits carry `reports/figures/` files, which some other tool regenerated; the loop writes none. A code change filed under a promotion message is hard to find, and reverting the promotion reverts it too. Reproduced in a scratch repository: the old command commits a staged `work.py` and a changed `reports/figures/plot.svg` along with the loop's three files. | `commit_promotion` commits `PROMOTION_FILES` with `git commit --only -- <files>`. Test, in a real repository: with `work.py` staged and a figure changed, the commit holds only the three files, and `work.py` is still staged afterwards. |
| P3 | **A failed commit went unnoticed.** `os.system`'s status was ignored. A promotion that could not be committed left `best_model.pt` and `config.json` changed on disk but not in git, for example because of a lock file, a hook, or a missing identity. `git checkout -- .`, `git stash` or a pull could then undo it, and nothing said so. | The exit of each git step is checked. A failure is printed and written to the cycle's sprint-log entry with git's reason, and the three files are unstaged again. Tests: outside a repository, `git add` failing is reported with git's `fatal:` line; a failing hook is reported by its `error:` line and leaves the index as it was; a failed commit is written to the cycle's entry, with the message the loop passed. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The logged reason was git's last output line, usually pre-commit's stash-restore message, not the failing hook or `fatal:` line. | Fixed: `fatal:`/`error:` lines and failed hooks are kept. Tested with a failing hook. |
| The 120 s timeout killed git with SIGKILL, leaving `.git/index.lock` and `next-index-<pid>.lock`; every later git command failed until they were removed by hand. | Fixed: SIGTERM after 300 s, on which git removes them. Tested: no lock remains (a SIGKILL leaves both, checked by hand). |
| Undecodable hook output raised `UnicodeDecodeError`, which would end the loop. | Fixed: decoded with replacement. |
| The real-repository test inherited `GIT_*` variables and the global config. | Fixed: both are isolated. |
| A failed commit left the three files staged for the operator's next commit. | Fixed: unstaged again. Tested. |
| The failure line was appended after the cycle's entry, and named two of the three files. | Fixed: in the entry, before its result, naming all three. Tested. |
| `--only` refuses during a merge or cherry-pick, and a staged `.pre-commit-config.yaml` blocks it; hooks set the operator's staged work aside while they run. | Recorded below. |
| The doc miscounted the earliest promotion commits and left ruff out of the hooks. | Corrected. |
| Tests lacked a partly staged file, a hook and the commit message. | Added. |

## Observations for the owner (not changed)

- **The commit runs the repository's pre-commit hooks** on the three files. None of them blocks it (checked in a
  clone with the real configuration):
  - `check-added-large-files` checks only newly added files (pre-commit-hooks v5.0.0), and `best_model.pt` is
    already tracked;
  - the text hooks skip the binary checkpoint;
  - `config.json` and `autoresearch_history.json` are excluded;
  - ruff, mypy and the document guards run only for `.py` and `.md` files.

  Under `--only`, pre-commit compares the working tree with git's temporary index. For the seconds the hooks run,
  it sets the operator's staged and unstaged work aside, and it restores it afterwards. This was tested with a hook
  that passes, one that fails, and one that modifies a file.
- **A partial commit is refused while a merge is in progress** ("cannot do a partial commit during a merge",
  checked with a conflicted merge; a cherry-pick in progress is expected to behave alike), so a promotion then fails
  and is logged. A staged `.pre-commit-config.yaml` makes every promotion fail too, with pre-commit's own message,
  until it is committed.

  A hook added later that fails would now be logged, not silently ignored.
- **`recent_configs.json` is tracked but not committed by the loop.** It changes every cycle (see the bandit-state
  review), and committing it would add a commit per cycle.
- **The 50 promotion commits stay as they are.** The 10 earliest (2026-03-25 to 04-11) carry sprint logs, 7 of
  them `train.py` changes too, from earlier versions of the loop.

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
- Branch, after the PR review's fixes: 42 failed, 2128 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 4 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py`, in isolated scratch repositories:
- a promotion commits only the loop's files (with staged work, a partly staged file and a changed figure, all left
  as they were);
- a failed promotion commit names the cause (a failing hook's `error:` line) and unstages the loop's files;
- a hung git is stopped without leaving its lock;
- a failed promotion commit is recorded (`git add` failing outside a repository; the cycle's entry; the message).

The loop tests' stubs moved from `os.system` to `commit_promotion`, including the lifecycle test that a failed cycle
attempts no commit.

Not verified here: a commit on the GPU host, with its installed hooks.
