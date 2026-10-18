# Design and architecture review — the handoff's villa upstream audit

Date: 2026-10-18. Baseline: `74e5b632` (main after #123). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/archive/audit_villa_upstream.py`, the post-sprint handoff's first step
(`scripts/run_post_sprint_villa_handoff.py`). It compares villa's checkout with its upstream and groups the
upstream changes into prize-relevant areas. Its JSON feeds two readers:
- `scripts/plan_villa_prize_opportunities.py`;
- `scripts/review_villa_pin.py`, whose report is the checklist before a pin update.

None of the three had a dedicated review. The 2026-10-16 prize-evidence review covered the handoff that runs them,
`review_villa_pin.py`'s legacy record and the opportunity plan's output path, not the audit itself.

## What changed

- **An uninitialised villa was audited as this repository.**
  - The audit checked only that `villa/` exists. An uninitialised submodule is an empty directory, and git run in
    one answers for the enclosing repository. That is a fresh clone, or a worktree before
    `git submodule update --init`.
  - Run here on an empty directory inside this checkout, it exited 0 and reported:
    - `local_ref` and `upstream_ref` both `74e5b632`, this repository's own HEAD and `origin/main`;
    - `behind: False`.

    So the pin review downstream would have called villa up to date.
  - `_check_own_repository` now refuses any villa directory whose `git rev-parse --show-toplevel` is not itself.
    It says where git answered and what to do:
    - git's own error, such as dubious ownership, is shown;
    - a work tree inside a `.git` directory points to `scripts/dev_worktree.sh repair`. That is a dev worktree
      made before #119, where the old audit's per-worktree HEAD was right but `submodule update` would rewrite
      the shared config.
    - an enclosing repository points to `git submodule update --init villa` in a clone, or to
      `scripts/dev_worktree.sh add`.
- **Git calls now ignore a hook's locator variables** (`GIT_DIR`, `GIT_INDEX_FILE`, ...), as
  `scripts/audit_doc_references.py` does. With `GIT_DIR` set, every call read that repository.
- **Moves are counted.**
  - The audit lists changes with `git diff --no-renames --name-only`.
  - With rename detection, a moved file is listed only at its new path, so the area it left counted nothing in the
    range that moved it. On `af8bac80e`, the move below, `--no-renames` lists 221 paths, both sides of each move.
    The independent review measured 111 with rename detection, none of them on the old side.
  - Rename detection also reads file contents. In villa's `blob:none` partial clone those are fetched over the
    network, or the diff fails offline. The docstring's "reads only git metadata" now holds.
- **Two prefixes tracked code that villa had deprecated.**
  - Villa #1486 (`af8bac80e`, 2026-08-17) deprecated the standalone ink-detection pipeline "in favor of
    villa/vesuvius/src/vesuvius/ink_detection". It moved `train_resnet3d_3d_decoder.py` and the
    `inference_*.py` scripts to `deprecated/ink-detection/`.
  - The `resnet3d_decoder` and `optimized_inference` prefixes for them have matched nothing since. Both prefixes
    are dropped. Each area keeps its file under `ink-detection/optimized_inference/`, which the pin still has.
  - No area tracks the replacement package (see the observations).
- **The audit now reports `stale_prefixes`:** the prefixes that match no file in the local and the upstream
  tree, read from trees alone. So a move shows on the first audit whose upstream contains it, before the pin
  follows.
- **`plan_villa_prize_opportunities.py`'s hook texts** named `generate_fiber_labels.py`, `train.py` and
  `predict.py` at their pre-June paths. They now give the current ones.
- **Tests.**
  - The two existing tests stub git and use an empty directory for villa, so they now stub the new check and tree
    read too. The first test's paths now include the deprecated file, counted in no area.
  - New tests, all with git's locator variables and global config removed:
    - an uninitialised villa in a repository with its own `origin/main` is refused (the old code exited 0 there),
      including under a hook-exported `GIT_DIR`;
    - each piece of advice, and git's own error, appears in the refusal;
    - a hook-style `GIT_DIR` does not redirect the audit;
    - a symlinked villa is accepted;
    - a file moved out of an area is counted in the range that moved it, and its prefix is reported stale
      upstream;
    - every prefix matches a file in the pinned tree, through the audit's own matcher. This one is skipped where
      the pin's objects are not available, or after 60 s, since a partial clone fetches missing objects lazily.

## Verified, no change needed

- **At the pin, run here,** the audit reports:
  - `local_ref` `ccb431818` and `upstream_ref` `b29f3109`, villa's `origin/main` as last fetched here (2026-10-17;
    the commit is dated 10-16);
  - one commit behind, not diverged;
  - 8 changed files, all under `foundation/`, so in no area;
  - no stale prefix in either tree.
- **The readers** read only the audit's JSON, and ignore its new key. Their tests and the handoff's pass.

## Observations for the owner (not changed)

- **No area tracks villa's current ink detection, `vesuvius/src/vesuvius/ink_detection/`** (51 files at the pin).
  - Nine of the commits between `af8bac80e` and the pin touch it. The pin commit itself changed its
    `preprocessing/create_label_zarrs.py`.
  - Nothing in this repository imports it, so whether it becomes an area, and with what risk and checks in
    `review_villa_pin.py`, is the owner's call.
- **The pin review's checks for the two high-risk areas cannot run as written.**
  - `uv run python scripts/smoke_test_villa_optimized_inference.py` exits 2 without `--output`, `--report` and
    `--command-out` (see `docs/CHECKPOINT_EXPORT.md`).
  - What the smoke validates is the checkpoint envelope, not villa's code.
  - `build_markdown_checklist` also lists only lasagna, Volume Cartographer and the prize docs. So the two areas
    that decide `hold_pin_until_required_tests_pass` never appear in `villa_pin_review.md`.
- **The committed audit and its two downstream reports date from June.**
  - `reports/villa_upstream_audit.json` (`fd1e9d2c`, 2026-06-04) describes a villa checkout at `64caeb2`, with six
    local commits and diverged from upstream.
  - The pin is now `ccb431818`, an upstream commit.
  - The handoff's next run regenerates all three. A run here would record this container's fetch of villa and its
    paths, so they are left.
- **The audit compares villa's checked-out `HEAD`, not the commit this repository pins.** The two agree here.
  While a pin bump is under review they differ, and the pin review then describes the checkout. Recording the
  gitlink beside `HEAD` would change the reports' meaning.
- **Any repository passed as `--villa-dir` is accepted**, the superproject itself included. Checking that it holds
  the superproject's gitlink commit would catch that.
- **The audit lives in `scripts/archive/`, yet the handoff's first step runs it.**
  - The 2026-06-02 cleanup archived it (`ebc7aab4`), and `06fcee7d` pointed the handoff at the archived path two
    days later.
  - Ruff and mypy still cover `scripts/archive/`, but tests exist for 2 of its ~30 scripts.

## Verification

Environment: CPython 3.10 venv, git 2.43. Villa at the pin, in a sparse blob:none checkout.

- `pytest tests/test_villa_upstream_audit.py tests/test_review_villa_pin.py tests/test_villa_prize_opportunities.py
  tests/test_post_sprint_villa_handoff.py`: 21 passed.
- **Mutation check.** Each mutation fails at least one test:
  - rename detection back on;
  - no upstream `stale_prefixes`;
  - the check on the return code only;
  - the check run with the hook's variables;
  - no repair advice;
  - git's error dropped;
  - a string comparison instead of `resolve()`;
  - a dead prefix restored.
- **The empty-villa reproduction:** the old script on an empty directory inside this checkout, as above.
- Ruff clean on the changed files.
- **Independent review** of the first commit. It found:
  - that the moved prefixes tracked deprecated code;
  - that rename detection hid moves and fetches blobs;
  - that the refusal's advice could break an absorbed villa;
  - that the readers' checks cannot run;
  - the overstated claims about earlier reviews and the prefix test;
  - smaller points.

  All are addressed above, or recorded as observations.
- The standard suite: see the PR.
