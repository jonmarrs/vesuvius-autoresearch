# Design and architecture review — the owner's #112, #118, #119 and #120

Date: 2026-10-18. Baseline: `1c30983d` (main after #122). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the four owner merges of 2026-10-17 that the last two reviews did not cover:
- #112: `scripts/promotion_cycle_gain.py` and `reports/promotion_cycle_gain_2026-10-17.*`;
- #118: the removal of `scripts/inference/production_predict.py`;
- #119: `scripts/dev_worktree.sh`, which gives each villa worktree its own `core.worktree`;
- #120: `scripts/epoch_boundary_overhead.py`, which starts a cycle's interval at a restart.

## What changed

- **Worktrees added before #119 could not be fixed with the script.**
  - With villa's `extensions.worktreeConfig` on, as in the owner's checkout, a villa worktree that `add` made before
    #119 takes villa's git directory for its work tree. #119's message names the hazard: `git status` there lists
    every file as deleted, and a restore or checkout writes into the git directory.
  - #119 fixed `add` only. A worktree made earlier stays broken, and `add` cannot make it again: it runs
    `git worktree add -b <branch>`, which refuses an existing branch.
  - Reproduced with the script as it was before #119 (`5a2840d7^`): the old worktree's `villa/` reports villa's git
    directory as its top level, with 13 status lines. The current `remove` does remove it cleanly (villa's status and
    `fsck` clean afterwards). Re-adding the branch then fails: "a branch named 'feature' already exists".
  - `dev_worktree.sh repair <branch>` sets the same `core.worktree` in place, under the same extension check, so it
    does nothing to the shared config when the extension is off. `add` and `repair` share that check.
    `docs/RESUME_AFTER_RESTART.md` names the command beside `add` and `remove`.
  - Three tests, each failing without its part of the change:
    - a worktree stripped of its `core.worktree` is repaired, after which `add` still refuses the branch and
      `remove` works;
    - without the extension, `repair` leaves the shared config alone;
    - `repair` refuses a missing worktree.

## Verified, no change needed

- **#118.** No reference to `scripts/inference/production_predict.py` remains. Every mention of `production_predict`
  in the README, `docs/VOLUME_INFERENCE.md`, the inference module and the tests names `scripts/production_predict.py`,
  which exists and is tested (`tests/test_production_predict.py`, in the standard suite).
- **#119.**
  - The fix is limited to the case it describes. Without the extension, `config --worktree` would write villa's
    shared config, and the existing test checks that `add` leaves it alone.
  - `remove` still refuses a villa worktree with local changes.
- **#112.**
  - The parser takes a cycle's incumbent from its verdict line and groups cycles by incumbent value. That relies on
    the log's six-decimal values, and the committed JSON's two segments (0.249348, 0.265762) show they hold.
  - The report's figures match the JSON: 50 scored cycles before the promotion, mean +0.0157, SD 0.0034, 49 clearing
    0.01; 17 after, mean −0.0004, SD 0.0031, none clearing 0.01.
  - "Clears 0.01" counts the margin alone, not the AP gate. The JSON records no lifts. The ones measured
    elsewhere sit far above 1.02: the probe's 1.17–1.21, and finding 88's candidates at 1.15 and up.
- **#120.** The parser now restarts a cycle's clock at the sprint log's `## Resumed at` line, which
  `run_autoresearch_loop.py` writes (`RESUME_MARKER`). The 75-cycle fit was recomputed in the previous review.

## Observations for the owner (not changed)

- **The resume marker is written once per run of restarts, so #120's clock can start early.**
  - `run_autoresearch_loop.py` writes `## Resumed at` only when the log does not already end with one. This is
    deliberate: a watchdog restarting a loop that runs no cycle would otherwise add a line every few minutes.
  - The parser restarts the clock at that first marker. So the first cycle after a run of restarts that ran no cycle
    has their whole span counted as its overhead. It stays in the fit unless the total passes the 600 s filter.
  - The 10-16/17 sprint logs are not committed, so whether this touched any of the three recovered rows could not
    be checked. `ema_decay_0.999`'s 203 s, against a median of 108 s for its group, is the candidate.
  - Recording each restart's time, for instance by updating the marker line in place, would be a change to the
    loop's log.
- **`add` cannot make a worktree for a branch that already exists.** That is `git worktree add -b`'s rule, and it
  predates #119. `repair` covers the villa case. Adding an existing branch would need `add` without `-b`.

## Verification

Environment: CPython 3.10 venv, bash 5, git 2.x. No scroll data.

- `pytest tests/test_dev_worktree.py`: 10 passed (7 before, 3 new).
- **Mutation check** on the script. Each mutation fails at least one test:
  - `repair` setting nothing;
  - `repair` without the extension check;
  - `repair` without the missing-worktree guard;
  - `add` without its `core.worktree`.
- **The pre-#119 reproduction:** a throwaway repository with a villa submodule and `extensions.worktreeConfig` on,
  the old script's `add`, then the current `remove`, or a manual `config --worktree` followed by `add`.
- `bash -n scripts/dev_worktree.sh`. Ruff clean on the test file.
- The standard suite: see the PR.
