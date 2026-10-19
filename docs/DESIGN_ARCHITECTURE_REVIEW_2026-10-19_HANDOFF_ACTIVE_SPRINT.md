# Design and architecture review — the post-sprint handoff's active-sprint guard

Date: 2026-10-19. Baseline: `20cdd109` (main after #130). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/run_post_sprint_villa_handoff.py`, the one-command Scroll 2/3 handoff that
`docs/VILLA_PRIZE_READINESS.md` prescribes.
- Its guard refuses to run while research is using the GPU. `--preflight-only` allows its non-GPU steps then.
- Its `--execute-inference` and `--execute-evidence` steps run on the GPU.

This round followed #124's change to the audit, the handoff's first step, into the code that decides whether the
handoff may run.
- The step itself is sound: `run_steps` uses `check=True`, so an audit that refuses an uninitialised villa stops
  the handoff. It does not go on to plan from the June `reports/villa_upstream_audit.json`.
- The guard was not sound.

## What changed

- **The guard did not see a noise probe, an ablation or a re-score.**
  - It ran `pgrep -af` with `run_autoresearch_loop.py|train.py|uv run python -u train.py`.
  - Three other kinds of GPU work take the loop's lock, and none runs under either name:
    - `scripts/f1_noise_probe.py`, whose trials train in-process in `scripts/training/run_noise_probe.py`;
    - `scripts/ablate_scroll_augmentations.py`, whose cells run `scripts/train_with_new_augs.py`;
    - `scripts/reevaluate_best_model.py`, as a script or as `-m scripts.reevaluate_best_model`.
  - Reproduced with `pgrep` and stand-in processes carrying those command lines: main's pattern missed all five,
    and saw only the loop and `train.py`.
  - So with `--execute-inference` or `--execute-evidence`, the handoff could start GPU work beside a multi-hour
    probe or ablation, on the same card.
- **The guard now asks the lock first, then checks names.**
  - `loop_control.running_pid(<checkout>)` names the lock's holder, as `start.sh`, `stop.sh`, the watchdog, the
    ablation and the re-score already ask it. A lock that cannot be read, or whose holder cannot be identified,
    also counts.
  - `loop_control.unsupervised_runs` adds a training run going in this checkout with no supervisor, for example
    one left by a killed ablation.
  - The name scan stays, because the GPU is shared and a probe in a dev worktree holds that worktree's lock. Its
    pattern is now built from:
    - `loop_control.LOCK_HOLDER_ARGS`, the set `running_pid` checks a holder against, lifted unchanged into a
      constant;
    - the training scripts `loop_control.RUN_SCRIPTS` lists;
    - `run_noise_probe.py`.
  - Each name must follow a space or `/` and end at a space or the end of the command line, so
    `tests/test_f1_noise_probe.py` in a pytest run is not one.
- **`loop_control.running_pid` refuses a lock it cannot parse, instead of crashing.**
  - It took any `isdigit()` string, and `int()` refuses some of those ("²"). Bytes that are not UTF-8 failed to
    decode. Either ended `loop_control.py status` in a traceback.
  - The traceback's exit 1 is what `start.sh` and the watchdog read as "nothing running", so they launched a loop
    beside the holder. That loop then failed to take the lock.
  - It now reads the lock with `errors="replace"` and requires an ASCII number, so either case is "contains no valid
    PID", exit 2, and nothing is launched.
  - The independent review found this.
- **Docs.** `docs/VILLA_PRIZE_READINESS.md`'s two descriptions of the guard, and the script's docstring, say what it
  checks.
- **Tests, all in the standard suite.**
  - In `tests/test_post_sprint_villa_handoff.py`, 9 new:
    - the pattern, through `pgrep` itself, against stand-in interpreters matched by PID. The stand-ins cover:
      - each lock holder, by path and as a module;
      - the probe's and the ablation's training;
      - the loop and `train.py`;
      - a pytest run, the handoff and an editor on `docs/train.py.md`, which must not match;
    - `active_sprint_processes` end to end, finding a running noise probe;
    - every name in `LOCK_HOLDER_ARGS` in the pattern;
    - this checkout's lock holder;
    - a lock that cannot be read: a `RuntimeError`, a `PermissionError` or a `ValueError`;
    - an unsupervised run;
    - nothing running.

    The `pgrep` tests skip off Linux, and without `pgrep`.
  - In `tests/test_loop_lifecycle.py`, `start.sh`'s exit-code test now also covers "²" and bytes that are not UTF-8
    in a held lock: exit 2, and nothing launched. Both fail with main's `running_pid`.

## Verified, no change needed

- **`loop_control.py`'s behaviour is unchanged.** `running_pid` tests the same names, now held in a module constant.
  Its tests pass: `test_loop_lifecycle`, `test_ablation_harness_isolation`, `test_noise_probe_contracts`,
  `test_checkpoint_tool_contracts`, and the suite guard.
- **The loop does not run the handoff,** so consulting the lock cannot block the loop's own call. The handoff is run
  by hand, per `docs/VILLA_PRIZE_READINESS.md`.
- **The handoff stops at the first failed step** (`check=True`), the audit's refusal of an uninitialised villa
  included.

## Observations for the owner (not changed)

- **The handoff does not take the lock while its GPU steps run.** A watchdog tick or `start.sh` can start the loop
  mid-handoff, and neither would see the handoff. This predates the change; taking the lock would make the handoff
  one more lock holder.
- **The `-m` forms of the training scripts are not named** (`scripts.training.train` and the like). `RUN_SCRIPTS`
  does not list them either, and the 2026-10-15 review found nothing runs them that way.

- **The name scan still sees only these names.** A new kind of GPU work that takes the lock under a new script name
  appears through `LOCK_HOLDER_ARGS` once `running_pid` learns it. One that does not take the lock is seen by
  neither check.
- **A process editing or viewing one of these scripts** (`vim scripts/training/train.py`) matches, as one did
  before. It blocks the GPU steps, in the safe direction.

## Verification

Environment: CPython 3.10 venv, procps `pgrep`.

- `pytest tests/test_post_sprint_villa_handoff.py` and the five `loop_control` test modules: all pass.
  - The handoff tests: 14 passed, with `.venv/bin` first on `PATH` as under `uv run`. Without `pgrep`: 12 passed,
    2 skipped.
- **The `pgrep` reproduction** above, with main's pattern and with this one.
- **Mutation check.** Each mutation fails at least one test:
  - main's pattern, in the constant or at the call site;
  - `pgrep -a` without `-f`;
  - no `pgrep` call;
  - either boundary dropped;
  - no lock check;
  - the lock of the working directory rather than the checkout's;
  - an unreadable lock not counted, or only a `RuntimeError` caught;
  - no unsupervised runs;
  - `run_noise_probe.py` left out;
  - `running_pid`'s old parsing.
- **Independent review** of the first commit. It found:
  - that the `pgrep` test's stand-ins (`exec -a … python3`) die under uv's interpreter, so the suite went red under
    `uv run` (blocking);
  - that the tests did not tie `active_sprint_processes` to the pattern;
  - that without `pgrep`, the stubbed tests failed;
  - the unparsable lock;
  - three inexact sentences.

  All are addressed above.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR.
