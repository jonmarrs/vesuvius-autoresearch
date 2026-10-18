# Design and architecture review — the handoff's villa upstream audit

Date: 2026-10-18. Baseline: `74e5b632` (main after #123). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/archive/audit_villa_upstream.py`, the post-sprint handoff's first step
(`scripts/run_post_sprint_villa_handoff.py`). It compares villa's checkout with its upstream and groups the
upstream changes into prize-relevant areas. Its JSON feeds the next two steps:
- `scripts/plan_villa_prize_opportunities.py`;
- `scripts/review_villa_pin.py`, whose report is the checklist before a pin update.

No earlier review covered these three scripts. Of the scripts the loop or the handoff runs, they were the ones with
no review at all, with `run_ranked_inference.py` and `launch_proofreader.py`.

## What changed

- **An uninitialised villa was audited as this repository.**
  - The audit checked only that `villa/` exists. An uninitialised submodule is an empty directory, and git run in
    one answers for the enclosing repository. That is a fresh clone, or a worktree before
    `git submodule update --init`.
  - Run here on an empty directory inside this checkout, it exited 0 and reported:
    - `local_ref` and `upstream_ref` both `74e5b632`, this repository's own HEAD and `origin/main`;
    - `behind: False` and `diverged: False`.

    So the pin review downstream would have called villa up to date.
  - `_check_own_repository` now refuses any villa directory whose `git rev-parse --show-toplevel` is not itself,
    naming `git submodule update --init villa`.
- **Git calls now ignore a hook's locator variables** (`GIT_DIR`, `GIT_INDEX_FILE`, ...), as
  `scripts/audit_doc_references.py` does. With `GIT_DIR` set, every call read that repository.
- **Two prize-area prefixes named files that villa had moved.** At the pin, `ink-detection/` holds only
  `optimized_inference/`.
  - `ink-detection/train_resnet3d_3d_decoder.py` (the `resnet3d_decoder` area) is at
    `deprecated/ink-detection/train_resnet3d_3d_decoder.py`.
  - The `ink-detection/inference_*` scripts (the `optimized_inference` area) are under `deprecated/ink-detection/`.

  Both prefixes matched nothing, so upstream changes to those files went uncounted. They now name the files'
  current paths, so the areas track the same files as before.
- **Tests.**
  - The two existing tests stub git and use an empty directory for villa, so they now stub the new check too. The
    first test's changed path moves to `deprecated/`, as at the pin.
  - New tests:
    - an uninitialised villa inside a scratch repository is refused;
    - a hook-style `GIT_DIR` does not redirect the audit (a scratch villa with its own `origin/main`);
    - every prize prefix exists in the pinned villa's tree, read with `git ls-tree`. This one is skipped where the
      pin's objects are not available.

## Verified, no change needed

- **At the pin, run here,** the audit reports `local_ref` `ccb431818` and `upstream_ref` `b29f3109` (villa's
  `origin/main` as last fetched here, 2026-10-16). That is one commit behind, not diverged, with 8 changed files
  in no prize area.
- **The other prefixes exist at the pin:**
  - `lasagna/`, `ink-detection/optimized_inference/` and its `model_resnet3d_3d_decoder.py`;
  - `volume-cartographer/`, `vesuvius/src/vesuvius/data/` and `scripts/build_chunk_occupancy.py`;
  - `scrollprize.org/docs/34_prizes.md`.
- **The readers.** `plan_villa_prize_opportunities.py` and `review_villa_pin.py` read only the audit's JSON, so
  the fix belongs in the audit. Their tests pass unchanged, and so does `test_post_sprint_villa_handoff.py`.

## Observations for the owner (not changed)

- **The committed audit and its two downstream reports date from June.**
  - `reports/villa_upstream_audit.json` (`fd1e9d2c`, 2026-06-04) describes a villa checkout at `64caeb2`, with six
    local commits and diverged from upstream.
  - The pin is now `ccb431818`, an upstream commit.
  - The handoff's next run regenerates all three. A run here would record this container's fetch of villa
    (2026-10-16) and its paths, so they are left.
- **The audit compares villa's checked-out `HEAD`, not the commit this repository pins.**
  - The two agree here. While a pin bump is under review they differ, and the pin review then describes the
    checkout.
  - Recording the gitlink beside `HEAD` would make that visible. That is a change to the reports' meaning, so it
    is left to the owner.
- **The audit lives in `scripts/archive/`, yet the handoff's first step runs it.**
  - The 2026-06-02 cleanup archived it (`ebc7aab4`), and `06fcee7d` pointed the handoff at the archived path two
    days later.
  - Ruff and the tests still cover `scripts/archive/`, so nothing goes unchecked. But "archive" no longer means
    "unused".
- **Upstream is whatever villa's `origin/main` was at its last fetch.** The docstring asks for a fetch first.
  Nothing records when that was.

## Verification

Environment: CPython 3.10 venv, git 2.x. Villa at the pin, in a sparse checkout.

- `pytest tests/test_villa_upstream_audit.py tests/test_review_villa_pin.py tests/test_villa_prize_opportunities.py
  tests/test_post_sprint_villa_handoff.py`: 16 passed.
- **Mutation check.** Each mutation fails at least one test:
  - the check not called;
  - the check on the return code only;
  - git run with the hook's variables;
  - each stale prefix restored.
- **The empty-villa reproduction:** the old script on an empty directory inside this checkout, as above.
- Ruff clean on the changed files.
- The standard suite: see the PR.
