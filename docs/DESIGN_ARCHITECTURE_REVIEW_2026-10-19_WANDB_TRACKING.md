# Design and architecture review — the loop's W&B tracking

Date: 2026-10-19. Baseline: `fac62ba1` (main after #135).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/wandb_tracking.py` and the calls `scripts/training/train.py` makes to it.
- `config.json` sets `use_wandb: true`, so every loop cycle, noise-probe trial and ablation cell opens a W&B run.
- Earlier reviews covered two pieces: its `finish_run`, after `run_result.json` (2026-10-14, failed cycles), and
  its no-op when disabled (2026-10-13).

## What changed

- **The W&B validation log did not carry what the loop selects on.**
  - `train.py` logs `val/val_bpb`, `val/dice`, the topology metrics, peak VRAM and throughput. That set was wired
    on 2026-06-10 (`d40b1545`).
  - On 2026-07-11 (`3e28b182`) the loop came to select on val_f1 gated by AP lift. Since then val_bpb and topology
    are reported only. The W&B log was not updated.
  - So no cycle's W&B run recorded its val_f1, its threshold, its AP lift, its ROC AUC, the incumbent it was compared
    with, or whether it was promoted. The dashboards showed only the numbers the loop no longer decides on.
  - It now logs these, under the names `run_result.json` uses:
    - `val/val_f1` and `val/val_f1_threshold`;
    - `val/ap_prevalence_lift` and `val/roc_auc`;
    - `val/incumbent_val_f1`, when there is an incumbent (it is -inf without one);
    - `val/is_success`.

    The existing keys are unchanged.
- **Tracking could still crash a cycle before its first step.** The module promises that "a tracking hiccup never
  crashes a training cycle". But:
  - if the offline fallback after a failed online init also raised, `init_run` raised;
  - with `use_wandb` set and wandb not importable, `init_run` raised `ImportError`.

  Either ended the run before training, as a crashed cycle, on every cycle until fixed. Each now prints a warning
  and returns no run, so every later helper is a no-op. That is how `finish_run` already treats a failure at the
  end (2026-10-14).
- **Tests** (`tests/test_wandb_tracking.py`, in the standard suite, 4 new):
  - online init failing, which falls back to offline;
  - offline failing too, which leaves the run untracked;
  - wandb missing, likewise;
  - `train.py`'s logged keys, read from its source, since the end of `train()` needs CUDA and data.

  With main's code, 3 fail. The first passes, and pins the existing fallback.

## Verified, no change needed

- **Disabled tracking touches nothing.** With `use_wandb: false`, or `WANDB_MODE=disabled`, `init_run` returns
  before importing wandb. `log` checks `wandb.run`, and the others check the run.
- **`finish_run`** reports, not raises, an exception after `run_result.json` (2026-10-14). The module's other
  helpers run only with a live run.
- **The training log's step.** `train/*` is logged every 10 steps at `step=step`. The validation log follows at the
  next step, and `wandb.watch`'s histograms attach to the current one.
- **The val/ keys log plain numbers.** `val_f1`, its threshold, the lift and the AUC are floats. `is_success` is a
  bool. The incumbent's `-inf` is left out rather than logged.
- **wandb is a declared dependency** (`wandb>=0.26.1`, locked at 0.26.1). It is absent only from this container's
  venv, which is why the end-to-end offline test skips here.

## Observations for the owner (not changed)

- **Every probe trial and ablation cell is a W&B run** with `job_type: autoresearch_cycle`, beside the loop's
  cycles. They read `config.json`, which has `use_wandb: true`. Nothing tells them apart but their config.
- **Runs are not named or grouped.** The loop sets no `WANDB_RUN_GROUP` and no run name, so a cycle's tweak is
  found from its logged config.
- **`wandb.watch(model, log="all", log_freq=100)`** logs every parameter's and gradient's histogram every 100 steps.
  Its cost on the loop's throughput has not been measured.
- **Local run files** go to `./wandb` in each run's working directory, which `.gitignore` excludes. Nothing prunes
  it.

## Verification

Environment: CPython 3.10 venv, without wandb (the end-to-end offline test skips).

- `pytest tests/test_wandb_tracking.py`: 9 passed, 1 skipped. With main's code, 3 of the 4 new tests fail.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR.
