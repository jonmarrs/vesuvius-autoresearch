# Design and architecture review — `dev_worktree.sh` when a step fails

Date: 2026-10-18. Baseline: `4bc9d2ce` (main after #127). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/dev_worktree.sh`'s `add` and `remove`, each a sequence of git and file steps, and what they leave
when a step fails. `docs/RESUME_AFTER_RESTART.md` sends all work outside the loop's checkout through them. The
2026-10-18 review of #119 (`DESIGN_ARCHITECTURE_REVIEW_2026-10-18_OWNER_MERGES.md`) added `repair` and recorded
that a failed `add` leaves a stray branch. This one follows every failed step to its end.

## What changed

Each case was reproduced with the script as on main, against the tests' throwaway repository.

- **`remove` dismantled the worktree before git refused it.**
  - `remove` removed villa's worktree and the four links, then ran `git worktree remove`. That refuses a worktree
    with modified or untracked files, so a single untracked file stopped it last.
  - The worktree was then left without villa and without `.venv`. Its tests and hooks no longer ran, and a second
    `remove` stopped at its first step: villa's worktree was gone ("is not a working tree"). Only manual git
    commands could finish it.
  - A locked worktree, which `git worktree remove` also refuses, ended the same way.
  - `remove` now checks, before it changes anything, each thing `git worktree remove` (git 2.43) refuses:
    - that the directory is one of this repository's worktrees, at its top level. In a directory inside a worktree,
      git answers for that worktree, so without the second check `remove feature/sub` would make
      `feature/sub/villa/` before git refused the path;
    - that it is not locked;
    - that it has no submodule repositories of its own (`<git dir>/modules`, left by a `git submodule update`
      there);
    - that its own files are clean (`git status --porcelain --ignore-submodules=all`), leaving out the four link
      names;
    - that villa's pointer is not staged. `--ignore-submodules=all` hides a staged gitlink, which git refuses; villa
      merely checked out at another commit, git accepts, and so does `remove`.

    It also checks two things of its own:
    - that each link name holds a link, or nothing. Those names are ignored, so `git worktree remove` would delete
      a real directory there with its contents, unasked. The old `rm` refused one (`Is a directory`);
    - that `villa/` is one of villa's worktrees, or empty.

    Villa's own `worktree remove`, which refuses villa's local changes, is then the first step that changes
    anything.
  - Each later step is skipped when already done, so a `remove` stopped between its steps resumes. One killed
    inside git's own deletion may need `git worktree prune`.
- **An `add` that stopped part-way could be neither finished nor removed.**
  - When villa's step fails after the outer worktree exists, `set -e` ends the script there. Reproduced with a
    base whose villa pin villa lacks: `invalid reference`. A pin bump that villa has not fetched, offline, is the
    realistic case.
  - `remove` then stopped at its first step, because villa had no worktree there, and `add` stopped on the branch
    that it had just made.
  - `remove` now skips a villa worktree that was never made, and `add` prints how to undo itself, in order:
    `remove <branch>` if the worktree exists, then `git branch -D <branch>` if the branch does. Paths are quoted
    for the shell.
  - `add` itself refuses a branch that exists, so a branch found when it stops is one it made, at the base, with
    no commits of its own.
  - The message comes from an EXIT trap, keyed on a flag set only once `add` has finished. Bash runs the trap on
    SIGINT and SIGTERM with `$?` reading 0, so a test of `$?` printed nothing for an `add` stopped with Ctrl-C.
    Villa's checkout, the slow step, is where that happens. The trap is set before the outer `git worktree add`,
    which can fail after making the branch: for example, in a post-checkout hook.
- **`add` onto a path in use left a stray branch.** `git worktree add -b` creates the branch before it refuses a
  non-empty path. The next `add`, after the path was cleared, then stopped on the branch. `add` now refuses such a
  path first: a file, a symlink, or a non-empty or unreadable directory. An empty directory, which git accepts, is
  still accepted.
- **Docs.** `docs/RESUME_AFTER_RESTART.md` says that a refused `remove` changes nothing, that a stopped one
  resumes, and that a stopped `add` says how to undo it.
- **Tests** (`tests/test_dev_worktree.py`, 13 new). Each case above:
  - the path in use, and then the empty directory; a file there; an existing branch; a base git rejects before
    making the branch, with no message;
  - the failed villa step, undone, then added again;
  - an `add` stopped by SIGTERM, and a successful one that prints no undo message;
  - a real directory at a link's name, which is kept;
  - a staged villa pointer, refused, and the same villa unstaged, removed;
  - submodule repositories of the worktree's own;
  - a worktree of a commit whose `.gitignore` does not match the links;
  - the refusal for an untracked file, with villa's worktree and the links still in place, then the removal;
  - a stopped `remove` resumed;
  - the locked worktree;
  - a missing name, a plain directory where git answers for the main checkout, and one inside a worktree;
  - a `villa/` that is not villa's worktree.

## Verified, no change needed

- **The links are ignored from 2026-10-13** (`313f3c29`, `039b2ba6`, `f6266534`). Before that, the patterns were
  for directories (`checkpoints/`), which do not match a link, so a worktree of an older commit lists them as
  untracked. The old script removed them before `git worktree remove` looked; the status check leaves their names
  out, which the link check above makes safe.
- **A pre-#119 worktree is still removable.** Its `villa/` git directory lies under villa's `worktrees/`, as for
  any other.
- **`add` for an existing branch** still stops at git, before anything is made.
- **Nothing outside the standard suite has rotted since its 2026-10-16 review.**
  - The 181 test modules outside `VALIDATION_TESTS` were run on main's tree, with this change's
    `dev_worktree.sh`: 16 failed, 1286 passed, 72 skipped, 21 errors.
  - Every failure and error has a cause that review recorded:
    - 19 `test_probe_*` modules need villa's spiral-fitting modules, absent here, and 2 need `s3fs`;
    - `s3fs` (5);
    - `umbilicus.json` (4), and `test_probe_real_patch_scatter`'s patches (1);
    - the LeJEPA checkpoint and villa's GP-winner config (2);
    - villa checked out as a directory (2);
    - the doc-reference guard (1): 17 villa paths outside this sparse checkout, and the ignored
      `models/detector/` checkpoint the detector reports cite;
    - `correlate_geometry_ink.py`'s host path (1).

## Observations for the owner (not changed)

- **`remove` deletes ignored files in the worktree.** `git worktree remove` does, and the status check, like git's,
  does not list them. That covers outputs written under ignored paths there. The links are removed first, so what
  they point to is not affected.
- **Commits made in villa's detached worktree are not checked.** Villa's `worktree remove` refuses local changes
  but not commits on its detached `HEAD`. Once removed, those commits are reachable from no ref, and villa's
  garbage collection can delete them.
- **A worktree whose directory was deleted by hand** is refused as "no worktree". `git worktree prune` forgets it.
- **Two tests outside the standard suite write into the checkout they run in,** both into ignored paths.
  - `test_villa_baselines_launchers` writes `scripts/_finetune_lejepa_runner.py`, as the 2026-10-16 review recorded.
  - `test_evaluate_villa_metrics` writes `outputs/skeleton_hists/skeleton_branch_length_hist_sample_1.png`.
    `scripts/evaluate_villa_metrics.py` saves villa's skeleton histogram there, and `train.py` saves the loop's
    histograms to the same directory, so in the main checkout the test replaces the loop's first one.
  - In a dev worktree, `outputs/` is the worktree's own.
- **`mypy`, which the pre-commit hook runs on the whole repository, is not in `uv.lock`.**
  - This container's `.venv` has mypy 2.4.0, installed on 2026-10-12. On main it reports 6 errors in 5 files, so
    here the hook would refuse every Python commit.
  - 4 errors are its "star unpack requires 3.11" on `a[(slice(None), *selection)]`, which Python 3.10 accepts:
    - `scripts/training/mutex_data.py`, twice;
    - `scripts/evaluate_deformation_metric.py`;
    - `scripts/compute_structure_tensors.py`.
  - The other 2 are `cv2` overloads given `np.float32([...])`: `repro/sota_data/register.py` and
    `tests/test_sota_register.py`.
  - Which mypy runs is whatever the `.venv` holds. Pinning it with the other tools would make the hook's result
    the same everywhere.

## Verification

Environment: CPython 3.10 venv, bash 5, git 2.43.

- `pytest tests/test_dev_worktree.py`: 29 passed (16 before, 13 new).
- **The three reproductions**, before and after, with the tests' fixture:
  - the path in use;
  - the pin villa lacks;
  - the untracked file, then a second `remove`.
- **Mutation check.** Each mutation fails at least one test:
  - no path check, or no branch check;
  - the undo message keyed on `$?`, or printed on success;
  - no status check, or one with `--ignore-submodules=none` or `=dirty`, or one that lists the links;
  - no staged-pointer, submodule-repository or link check;
  - an unconditional `mkdir` or `rm`;
  - no lock check;
  - no worktree check, or no top-level check;
  - no check of `villa/`'s contents;
  - villa's step run unconditionally, as on main.
- The undo commands, as printed, run from a main checkout under a path with a space, after a failing
  post-checkout hook, and leave one worktree and no branch.
- `bash -n scripts/dev_worktree.sh`. Ruff clean on the test file.
- **Independent review** of the first commit. It found:
  - that a real directory at a link's name, which the old `rm` refused, would now go with the worktree
    (blocking);
  - that a staged villa pointer, and a worktree's own submodule repositories, still let git refuse after the
    dismantling;
  - that the status check listed the links in a worktree of a commit before 2026-10-13, which the old script
    removed;
  - that the undo message was lost on SIGINT and SIGTERM, and on a failure inside the outer `git worktree add`;
  - that a directory inside a worktree passed the worktree check;
  - unquoted paths in the message, an unreadable directory, test gaps, and three overstated sentences.

  All are addressed above. Not addressed: `add` onto the path of a worktree that is registered but missing, on
  another branch (git makes the branch, then refuses). `git worktree prune` clears it.
- The standard suite: see the PR.
