# Design and architecture review — the README and the agent instructions against the code

Date: 2026-10-16. Baseline: `de3e0093` (main after #90 and #92). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what `README.md` and `docs/program.md` tell a person or an agent to run, and what those commands do: the
quick start, the loop's description, its controls and its records. Each claim was checked against the code it names.
Also in scope: one defect found on the way, in how `train.py` reports a missing villa metric.

## What changed

- **The quick start runs what it says.**
  - Its data step ran `scripts/archive/download_data.py --fragment 4`. That entry names `scripts/download_paris2fr47.py`,
    which now lives in `scripts/archive/`, so the command prints an error, downloads nothing and exits 0. Its own size
    label is ~104 GB, not "~5 min", and the archived script it would run fetches raw CT, not the labeled surface zarrs
    `config.json` reads. The step is replaced by a description of the data the loop needs (both zarrs, the label file,
    `mask.png`, the optional `patches.json`) and a plain statement that no maintained command builds it.
  - Its "smoke test (~30 s) to verify your setup" was `train.py --test`. That is a training run with a 30 s budget and
    the full 400-patch validation. It needs CUDA, takes no lock (so it can run beside the loop), and writes
    `history.tsv`, `last_model.pt` and `run_result.json`; if it beats the incumbent it replaces `best_model.pt`. The
    checks are now `make smoke` (no data, no GPU) and `train.py --smoke` (the model and one forward/backward on the
    CPU), neither of which writes anything. The README says why to avoid `--test`.
  - It now checks out the villa submodule. Without villa the re-score refuses (its skeleton metric is NaN), the
    `batchgeneratorsv2` augmentation mode raises, and the topology diagnostics are missing.
  - It now re-scores the incumbent before the first `./start.sh` (below), and says where the loop's refusal is
    written: `start.sh` reports the launch, and the loop's output, including `Not starting: …`, goes to
    `autoresearch.out`.
  - It notes the runbook's warning against `uv sync` on a host whose `vesuvius` package came from `villa/vesuvius`.
- **The controls are described as they behave.** The loop exits at each shift boundary (07:00 and 19:00, system local
  time); the watchdog, `scripts/loop_watchdog.sh`, restarts it, but nothing said what it was or how to install it. The
  README now gives its two crontab lines and its log. `start.sh` clears the pause even when it then refuses, because
  other work holds the lock, so an installed watchdog starts the loop once that work ends; the README says so.
- **The loop is described as it is.**
  - "Samples architectures, loss functions, augmentations" and "families (LR, Architecture, Loss Balance)": the
    architecture family holds only `resenc_unet`, already the configuration's, so it is never sampled; model size is
    pinned too, so every cycle warm-starts from `best_model.pt`. The tunable families are listed, with the weighting
    (×0.95 a scored cycle, floor 1; +1 a promotion).
  - "Calibration baselines: periodic re-evaluation against the 2023 Grand Prize recipe": removed from the loop on
    2026-10-12. The noise probe, which is run by hand, replaces the bullet.
  - `vesuvius_model.py` is not "the loop's architecture zoo": the loop's `resenc_unet` is built by
    `core/model_wrappers.py`, which inference shares. The project structure and `docs/program.md` say so; the agent
    instructions now list that file among the ones to read and change.
- **The records are described as they are written.**
  - `history.tsv` has a row for every `train.py` run that finishes validation, by hand too (not the noise probe's or
    the ablation's), and no val_f1, the metric that decides promotion (it is in `sprint_logs/` and `run_result.json`).
  - `results.tsv` is local (gitignored), has one row per promotion, states the bar, and has no val_f1 column.
    `.gitignore`'s comment that kept it "tracked/visible" contradicted its own entry and is corrected.
  - `prize_readiness.tsv` has one row per promotion, not per cycle, and its gates do not block promotion while
    `enforce_prize_gates` is false (as in `config.json`). A promotion the loop undoes loses its rows in both files.
  - `run.log`, `autoresearch.out` and `watchdog.log` are named.
- **The agent instructions** (`docs/program.md`) had the same errors: the download example, `--test` as a "30s smoke",
  and the prize window as a promotion gate (only with `enforce_prize_gates`, which `config.json` turns off). The
  real-signal gate is AP lift > 1.02, not > 1. They now say that a direct `train.py` run takes no lock and writes the
  loop's state.
- **A missing villa centerline metric is reported as unmeasured** (`scripts/training/train.py`). Without
  `metrics.centerline_dice`, its stand-in returned 0.0 for every patch, which counted as a sample. `history.tsv`
  recorded `avg_centerline_dice` 0.0 as a measurement, and the prize gates failed it as "below gate" rather than as
  missing. It now returns NaN, as the skeleton metric's stand-in does, and validation prints that the metric is
  unavailable. The pass then counts no samples, and an average over none is NaN (`mean_or_nan`, which the five
  topology averages now share; the centerline one alone gave 0.0), so the gates say "not finite" and "only 0
  centerline-dice samples". The threshold search falls back.
- The Makefile's comment said shifts change at 07:00 and 19:00 PT; they follow the system clock's local time.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | **The quick start cannot start a cycle, and says nothing about why.** The committed `best_model.pt` was scored under `seeded-sample-400-v2+z1-27`; the loop requires `seeded-sample-400-v3+z1-27` (since `ff13ee15`). `check_incumbent` raises, the loop prints `Not starting: …` to `autoresearch.out` and returns, while `start.sh` reports that it started. The watchdog relaunches it every tick, to the same refusal. | The re-score is step 5, with why and when to repeat it; the README says where the refusal is written. The re-score itself needs the GPU host and the data, so it is the owner's (below). |
| P2 | **The data step downloads nothing and exits 0**, and names a 104 GB raw volume that is not what the loop reads. | Replaced with what the loop needs; no maintained command is claimed. |
| P2 | **The setup check is a training run that can replace the incumbent**, beside the loop if one is running. | `make smoke` and `train.py --smoke`; `--test` explained. Also in `docs/program.md`. |
| P3 | **A missing villa centerline metric was recorded as 0.0.** | NaN, as for the skeleton metric; reported. Tests: with the module blocked, `train` records the import error, the stand-in returns NaN, and the search falls back; an average over no samples is NaN, and the gates call it not finite, not below the gate. Both fail on main. |
| P3 | **The villa submodule, the watchdog's installation, shift exits and the pause side effect were not documented.** | Documented. |
| P4 | The loop's tuning, the removed baseline, the model's file, the three TSVs and the logs were described wrongly or not at all; the agent instructions repeated several of these. | Corrected. |

## Review of the PR, and what it changed

The independent review of the PR's first head (`d9946894`) found nothing blocking. It confirmed the incumbent's
protocol and the re-score command, the promotion bar, the undo of promotion rows, the family weighting, the shift
times, the lock and pause behaviour, `uv sync`'s exactness, the broken data step, both smoke checks and every link.

| Finding | Outcome |
| --- | --- |
| P2: the centerline fix stopped halfway. With no samples, `train()` still averaged to 0.0 (`if … else 0.0`), so `history.tsv`, the checkpoint and the gates still recorded 0.0 and "below gate". The new test did not reach the aggregation. | Fixed: `mean_or_nan`; tested with the gates. |
| P3: val_f1 is not logged to wandb; the README said it was. | Corrected: `sprint_logs/` and `run_result.json`. Noted below. |
| P3: dropout was listed as tuned; the loop applies it only to `gated_unet`, and `resenc_unet` is pinned. | Removed. |
| P4: the mask is optional and `patches.json` replaces the training catalogue too; `pseudo_label_dir` was not mentioned. The probe and the ablation do not write `history.tsv`. The `--test` paragraph left out `results.tsv`, `prize_readiness.tsv` and the stale `config.json`. Step 5: the GPU is advised, not required; the re-score is also needed after the validation inputs change; it rewrites a tracked file. `make smoke` writes caches with data. Cron's `PATH` lacks `uv`. The probe needs `--config`, `--checkpoint` and `--out`. `make install` is `uv sync`. wandb is online by default. `run.log.old` is tracked. Three stale lines in `docs/program.md`. The placeholder below. | All corrected in the README, `docs/program.md` or here. |
| P4: `select_topology_threshold` returns a score of 0.0 when it measured nothing. | Left: the score is only printed (`train.py`, `reevaluate_best_model.py`), and an existing test pins it. |

## Observations for the owner (not changed)

- **As committed, the loop starts no cycle until `best_model.pt` is re-scored under v3.**
  - Run with the loop stopped, on the GPU host with the validation fragment:
    `uv run python scripts/reevaluate_best_model.py --update-stored`.
  - `ff13ee15`'s message gives `--update-stored --unwarped`. The incumbent already records `use_lasagna: false` (since
    its 2026-10-13 re-score), so `--unwarped` changes nothing now.
  - The same message asks for the noise probe under v3 before restarting; the 2026-10-16 training-data review repeats
    that. The tolerance is the owner's decision.
  - v3 scores the ink-free patches too, so the stored 0.7273 (v2) will change.
- **No maintained command builds the loop's data.** The labeled surface zarrs, their labels and masks come from
  outside the repository's maintained tools. A data-preparation script, or a documented manual path, would let the
  quick start be followed on a new host.
- **`train.py --test` takes no lock.** Run by hand beside the loop, it can promote over the loop's incumbent while a
  cycle runs. The lock holders (the probe, the ablation, the re-score) refuse beside the loop; `train.py` run by hand
  does not. Taking the lock in `train.py` would change how the loop's own cycles start, so it is left as documented.
- **val_f1, AP lift and AUC are not logged to wandb.** The wandb validation log has the reported-only metrics
  (`val_bpb`, Dice, topology, mean AP) but not the ones that decide promotion; adding them to `train.py`'s
  `wandb_tracking.log` call would put the dashboard on the promotion metric.
- **`run.log.old` is tracked** (since `c144a462`, June), 10.5 MB, so every rotation rewrites a tracked file. Untracking
  it upstream would delete the host's copy on pull, or stop the pull while that copy differs, so it is left to the
  owner.
- **`start.sh` clears the pause before it checks the lock.** Documented rather than changed: moving the clear after
  the check would change what `./start.sh` means when it refuses (today: "start when free"). It is the owner's choice.

## Reviewed and accurate

Every relative link in the README and every path in its project structure exists. The descriptions of `start.sh`,
`stop.sh`, the lock and its holders, `loop_control.py status`, the shift budgets (900 s and 3600 s), the per-cycle
preflight, the detector CLI flags and defaults, `production_predict`'s flags, the validation command and the
S3-gated test, the submission dry runs, and the training heads in `config.json` match the code.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy; villa present at the pin.

- Baseline: main `de3e0093`, 42 failed, 2476 passed, 21 skipped, 1 xfailed, 2 errors. The failures and errors are
  environmental: no scroll data, no CUDA, no villa data files.
- Branch, PR first head (`d9946894`): 42 failed, 2477 passed, 21 skipped, 1 xfailed, 2 errors. Same set; the extra
  pass is the new test. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped (no training data).
- Branch, after the PR review's fixes (`3c90dc4f`): 42 failed, 2478 passed, 21 skipped, 1 xfailed, 2 errors. Same
  set; the 2 extra passes are the two new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- `tests/test_topology_threshold.py`: 6 passed; `tests/test_prize_promotion_gates.py`: 5 passed, 1 skipped. Both new
  tests fail on main. The README-reading consistency tests
  (`test_withdrawn_claims_stay_withdrawn`, `test_decoupling_not_claimed_on_current_code`,
  `test_headline_numbers_consistent`, `test_villa_optimized_inference_smoke`): 40 passed.
- Ruff (check and format) and mypy on the changed Python files: clean.

New tests:
- `tests/test_topology_threshold.py::test_a_missing_centerline_metric_is_not_measured`;
- `tests/test_prize_promotion_gates.py::test_a_pass_without_centerline_samples_records_it_unmeasured`.

Not verified: the re-score, `train.py --smoke` and the loop on real data (no GPU, no scroll data here), and the
crontab lines on a host.
