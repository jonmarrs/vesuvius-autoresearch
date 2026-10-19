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
    - a full run trained the defaults for its budget and wrote the loop's state (`history.tsv`, `last_model.pt`,
      `run_result.json`).

      It could not promote over the tracked `best_model.pt`: the defaults' validation protocol has no depth band,
      and `promotion_decision` fails closed on an incumbent scored under another. It could bootstrap a
      `best_model.pt` where there was none, or replace one scored without a band.

    Either way it left a new config file behind. Reproduced with main's `train.py --smoke --config <missing>`: it
    wrote the file before failing for want of this container's data.
  - The loop is the only maintained caller of `train.py`'s command line, and it writes `config_temp.json` before its
    preflight and run. The noise probe and the ablation call `train.train`, which this does not touch. The
    documented commands use the tracked `config.json`. So nothing relied on the defaults being written.
  - The loop's own `load_current_config` still falls back to the defaults when `config.json` is missing, and writes
    them to `config_temp.json`. That is the first-run bootstrap; the start-up incumbent check refuses it over a
    `best_model.pt` scored on another protocol.
  - `train.load_run_config` now exits with "`<path>` does not exist; --config names the config to run", before
    anything is built. A loop cycle whose `config_temp.json` went missing now fails its preflight with that line,
    where before it trained the defaults under the cycle's tweak name.
- **Tests** (`tests/test_autoresearch_measurement.py`, 2 new, 3 cases):
  - `load_run_config` refuses a missing path, writes nothing, and loads one that exists;
  - the command line itself, with `--smoke` as the loop's preflight passes it and as a full run, exits 1 with the
    message, prints no `PREFLIGHT OK` and creates no file.
    - It runs from another directory, so a regression to the defaults fails for want of their data rather than
      training on this checkout's.
    - Each case takes about 4 s, for `train.py`'s imports.

  All fail with main's `train.py`. Each case kills a fallback to the defaults that the others miss, the full run's
  included.

## Verified, no change needed

- **`run_villa_prize_evidence_chain.py`**, the handoff's `--execute-evidence` step, reviewed on 2026-10-16.
  - Before anything but creating its output directory, it removes the four files a review reads:
    `evidence_metadata.json`, `manifest.json`, `neural_tracing.json` and `validation_report.json`. It then writes a
    failing `PRIZE_READINESS_REPORT.json`.
  - An earlier attempt's `candidate.json` and `predict_command.sh` stay until this run rewrites them. If this run
    fails first (a candidate the table no longer has), the old `candidate.json` remains; the descriptive
    `cross_scroll_validation.py` reads it.
  - It refuses a prediction that did not refresh its image. `predict.py` deletes its metadata sidecars before
    writing, so a stale sidecar cannot pass either.
  - Its refresh check compares `os.stat` results, whose times are whole seconds. A read of the old image without a
    rewrite would pass, and a rewrite in the same second would not. Neither happens in practice: nothing in the
    chain reads the image between the checks, and `predict.py` runs far longer than a second.
- **`promotion_cycle_gain.py`**'s patterns match what the loop prints:
  - `Starting with incumbent …`;
  - `Cycle N: Applying …`;
  - `Running N-minute training …`;
  - `No improvement. (val_f1: …, best was: …)`;
  - `IMPROVEMENT FOUND!`;
  - `CYCLE CRASHED`, the OOM form included.

  A cycle with no incumbent would be dropped, which cannot happen after the start-up its analysis counts from. So
  would a val_f1 below 1e-4, which Python prints in exponent form; only a collapsed model scores that.
- **The noise probe's strict JSON.** `f1_noise_probe.py` drops `max_prize_skel_dist` when it is the dataclass's
  `inf` default before its `json.dumps(..., allow_nan=False)`. `config.json` sets 2.0 in any case.

## Observations for the owner (not changed)

- **`ExperimentConfig()` prints its leakage warning** whenever it is built with the default `unlabeled_uris`, which
  include the default `val_uri`. Tests and tools that build defaults print it each time. Changing the default list
  would change every config built from defaults.
- **`ExperimentConfig.save` writes in place.** The loop renames `config_temp.json` over `config.json`, so the loop's
  own writes are atomic. A hand-run `save` to `config.json` is not.

## Verification

- `pytest tests/test_autoresearch_measurement.py`: all pass, the new cases included. With main's `train.py`, they
  fail.
- `train.py --smoke --config <missing>` by hand: exit 1, the message, no file.
- **Independent review** of the first commit found:
  - the promotion claim, overstated;
  - the caller list, which named callers of `train.train`;
  - a surviving mutation: a full run falling back to the defaults;
  - the test's working directory;
  - four inexact sentences.

  All are addressed above.
- Ruff clean on the changed files. No new mypy errors.
- The standard suite: see the PR.
