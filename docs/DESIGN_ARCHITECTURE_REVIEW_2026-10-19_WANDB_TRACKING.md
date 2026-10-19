# Design and architecture review — the loop's W&B tracking

Date: 2026-10-19. Baseline: `fac62ba1` (main after #135).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/wandb_tracking.py` and the calls `scripts/training/train.py` makes to it.
- `config.json` sets `use_wandb: true`, so every loop cycle and every ablation cell opens a W&B run.
- Noise-probe trials do not: `f1_noise_probe.py` writes `use_wandb: false` and `WANDB_MODE=disabled` into each
  trial, and `run_noise_probe.py` refuses one that tracks.
- Earlier reviews covered two pieces: its `finish_run`, after `run_result.json` (2026-10-14, failed cycles), and
  its no-op when disabled (2026-10-13).

## What changed

- **The W&B validation log did not carry what the loop selects on.**
  - `train.py` logs `val/val_bpb`, `val/dice`, the topology metrics, peak VRAM and throughput. That set was wired
    on 2026-06-10 (`d40b1545`).
  - On 2026-07-11 (`3e28b182`) the loop came to select on val_f1 gated by AP lift. Since then val_bpb and topology
    are reported only. The W&B log was not updated.
  - So no cycle's W&B run recorded its val_f1, its threshold, its AP lift, its ROC AUC, the incumbent it was compared
    with, or `promotion_decision`'s verdict.
  - `wandb_tracking.selection_metrics` now builds these entries, under the names `run_result.json` uses:
    - `val/val_f1` and `val/val_f1_threshold`;
    - `val/ap_prevalence_lift` and `val/roc_auc`;
    - `val/incumbent_val_f1`, left out when there is no incumbent (-inf) or it cannot be compared (NaN);
    - `val/is_success`, the verdict as a bool. For a run with `checkpoint_out`, such as an ablation cell, it says
      the run would have been promoted, not that it was.

    `train.py`'s validation log adds them; its existing keys are unchanged.
- **Tracking could crash a cycle.** The module promises that "a tracking hiccup never crashes a training cycle".
  But five of its calls could raise into the run, at init and mid-run:
  - **At init.** If the offline fallback after a failed online init also raised, `init_run` raised. With
    `use_wandb` set and wandb not importable, it raised `ImportError`. Either ended the run before training, on
    every cycle until fixed. Each now prints a warning and returns no run. With `WANDB_MODE=offline`, a failed init
    is no longer retried in the same mode, and the message no longer says it falls back.
  - **Mid-run.** `log`, `log_prediction_image` and `watch_model` called wandb unguarded, if the wandb service died
    mid-run, say.
    - The validation log and its image come before `save_cycle_checkpoints` and `run_result.json`. So a raise
      there discarded a scored cycle and any promotion: the harm `finish_run` was fixed for on 2026-10-14, earlier
      in the run.
    - A raise in the `train/*` log, every 10 steps, ended the run after its GPU time was spent.
    - Each is now reported once per kind and swallowed.

    The independent review found the mid-run calls.
- **Tests** (`tests/test_wandb_tracking.py`, in the standard suite, 7 new, 9 cases):
  - online init failing, which falls back to offline;
  - offline failing too, which leaves the run untracked;
  - offline mode failing, which is not retried;
  - wandb missing;
  - log, image and watch failures mid-run, each reported once and not raised;
  - `selection_metrics`, with an incumbent, with none, and with one that cannot be compared;
  - `train.py`'s validation log carrying `selection_metrics` with `train()`'s own values. It reads the source,
    since the end of `train()` needs CUDA and data.

  With main's code, 8 of the 9 fail. The first passes, and pins the existing fallback.

## Verified, no change needed

- **With tracking disabled, the helpers do nothing.** With `use_wandb: false`, or `WANDB_MODE=disabled`, `init_run`
  returns before importing wandb. `log` checks `wandb.run`, and the others check the run.
  - `train.py` itself imports wandb at import time, whatever `use_wandb` is, and wraps `wandb.log` so it does
    nothing without a run.
  - That import catches only `ImportError`. Any other failure to import wandb (a dependency clash) stops
    `train.py` before `init_run` is reached. That is a broken environment, and it is left loud.
- **`finish_run`** reports, not raises, an exception after `run_result.json` (2026-10-14).
- **The new entries are plain numbers.** `val_f1`, its threshold, the lift and the AUC are floats, possibly NaN. NaN
  was already logged (`train/total_loss` on a skipped step). `is_success` is a bool.
- **A failed init leaves no run behind** in the normal case, so `log`, which checks `wandb.run`, is then a no-op.
  The retry passes `reinit=True` as the first try did.
- **wandb is a declared dependency** (`wandb>=0.26.1`, locked at 0.26.1). It is absent only from this container's
  venv, which is why the end-to-end offline test skips here.

## Observations for the owner (not changed)

- **Every ablation cell is a W&B run** with `job_type: autoresearch_cycle`, beside the loop's cycles. Its config is
  all that tells it apart.
- **Runs are not named or grouped.** The loop sets no `WANDB_RUN_GROUP` and no run name, so a cycle's tweak is
  found from its logged config.
- **`wandb.watch(model, log="all", log_freq=100)`** logs every parameter's and gradient's histogram every 100 steps.
  Its cost on the loop's throughput has not been measured.
- **Local run files** go to `./wandb` in each run's working directory, which `.gitignore` excludes. Nothing prunes
  it.
- **Where the validation entries land among the steps** has not been checked against wandb here. The `train/*`
  rows are logged at `step=step`, and the validation log without a step.

## Verification

Environment: CPython 3.10 venv, without wandb (the end-to-end offline test skips).

- `pytest tests/test_wandb_tracking.py`: 14 passed, 1 skipped. With main's code, 8 of the 9 new cases fail.
- `test_autoresearch_measurement` and the suite guard with it: all pass.
- **Mutation check.** Each mutation fails a test:
  - each guard removed (log, image, watch);
  - reporting every failure;
  - logging the incumbent unconditionally;
  - `is_success` not cast;
  - the same-mode retry;
  - raising on `ImportError` or on the offline failure;
  - a wrong value wired in `train.py`;
  - `selection_metrics` not called.
- **Independent review** of the first commit. It found:
  - the mid-run calls;
  - that probe trials do not track;
  - three surviving mutations of the source test: a key moved to another log, a wrong value, the incumbent guard;
  - the offline-retry message;
  - the NaN incumbent;
  - `is_success`'s meaning for ablation cells;
  - the import-time patch;
  - a step claim it could not check.

  All are addressed above. The step claim is now an observation.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR.
