# Design and architecture review — the config a training run is given

Date: 2026-10-19. Baseline: `b7e83884` (main after #136).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `scripts/training/train.py`'s command line chooses the config it trains on, or checks with `--smoke`.
This round also read `scripts/run_villa_prize_evidence_chain.py` and `scripts/promotion_cycle_gain.py`. They were
among the loop's least-reviewed modules, and they needed no change (below).

## What changed

- **A `--config` that did not exist was written with the defaults, and run.**
  - `train.py`'s `__main__` loaded `--config` if it existed. Otherwise it saved `ExperimentConfig()`'s defaults to
    that path and went on with them. The defaults are not the loop's:
    - `architecture: gated_unet`, not `resenc_unet`;
    - no depth band;
    - `use_wandb: false`;
    - `num_layers` 24, not 16.
  - So a mistyped path ran a different model under it:
    - `--smoke` checked the defaults and could print `PREFLIGHT OK`, though step 4 of the README calls it the check
      of "the loop's configuration" that "writes nothing";
    - a full run trained the defaults for its budget, and could promote over `best_model.pt`.

    Either way it left a new config file behind. Reproduced with main's `train.py --smoke --config <missing>`: it
    wrote the file before failing for want of this container's data.
  - Every maintained caller writes its config first:
    - the loop writes `config_temp.json` before its preflight and run;
    - the noise probe writes each trial's;
    - the ablation goes through `train.train`.

    So nothing relied on the defaults being written.
  - `train.load_run_config` now exits with "`<path>` does not exist; --config names the config to run", before
    anything is built. A loop cycle whose `config_temp.json` went missing now fails its preflight with that line,
    where before it trained the defaults under the cycle's tweak name.
- **Tests** (`tests/test_autoresearch_measurement.py`, 2 new):
  - `load_run_config` refuses a missing path, writes nothing, and loads one that exists;
  - the command line itself, with `--smoke` as the loop's preflight passes it, exits 1 with the message, prints no
    `PREFLIGHT OK` and creates no file. It takes about 8 s, for `train.py`'s imports.

  Both fail with main's `train.py`.

## Verified, no change needed

- **`run_villa_prize_evidence_chain.py`**, the handoff's `--execute-evidence` step, reviewed on 2026-10-16. Since
  then it still removes the files of an earlier attempt, and writes a failing `PRIZE_READINESS_REPORT.json`, before
  anything that can raise.
  - It refuses a prediction that did not refresh its image. `predict.py` deletes its metadata sidecars before
    writing, so a stale sidecar cannot pass either.
  - Its refresh check compares `os.stat` results, which include whole-second access times. A read of the old image
    without a rewrite would pass, but nothing in the chain reads it between the two checks.
- **`promotion_cycle_gain.py`**'s patterns match what the loop prints:
  - `Starting with incumbent …`;
  - `Cycle N: Applying …`;
  - `Running N-minute training …`;
  - `No improvement. (val_f1: …, best was: …)`;
  - `IMPROVEMENT FOUND!`;
  - `CYCLE CRASHED`, the OOM form included.

  A cycle with a non-numeric score or no incumbent would be dropped. Neither can occur after the start-up its
  analysis counts from.
- **`config.json`'s `max_prize_skel_dist`** is 2.0. So the noise probe's `json.dumps(..., allow_nan=False)` of the
  config does not meet the dataclass's `inf` default.

## Observations for the owner (not changed)

- **`ExperimentConfig()` prints its leakage warning** whenever it is built with the default `unlabeled_uris`, which
  include the default `val_uri`. Tests and tools that build defaults print it each time. Changing the default list
  would change every config built from defaults.
- **`ExperimentConfig.save` writes in place.** The loop renames `config_temp.json` over `config.json`, so the loop's
  own writes are atomic. A hand-run `save` to `config.json` is not.

## Verification

- `pytest tests/test_autoresearch_measurement.py`: all pass, the 2 new included. With main's `train.py`, both fail.
- `train.py --smoke --config <missing>` by hand: exit 1, the message, no file.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR.
