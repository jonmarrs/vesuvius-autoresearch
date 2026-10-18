# Design and architecture review — the pooled v3 noise probe (#109)

Date: 2026-10-18. Baseline: `0580e5a7` (main after #114). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #109 (merged as `f85e0f7d`):
- the pre-registration `docs/preregistration/2026-10-17_noise_probe_v3_pooled.md`;
- the analysis `scripts/noise_probe_pooled.py`;
- its result `reports/noise_probe_v3_pooled_2026-10-17.{json,md}`, and batch 2's `reports/noise_probe_v3_2026-10-17.json`;
- `tests/test_noise_probe_pooled.py` and `tests/test_noise_probe_v3_pooled_report.py`;
- the note in `docs/RESUME_AFTER_RESTART.md`.

The tolerance and the study's design are the owner's. This review checks the analysis against its registration
and against the probe it reads, and the claims against the committed data.

## What changed

- **The analysis pooled trials without the checks the probe makes.**
  - `scripts/f1_noise_probe.py` reports a spread only when every trial shares one validation sample and
    prevalence. `docs/REPEATABILITY_PROBE.md` puts it so: "otherwise the scores are not the declared same-sample
    comparison and no spread is reported". It checks this only within a batch, and only when every trial
    finished.
  - `noise_probe_pooled.py` read each batch's finished trials and pooled them. It checked the batch's protocol,
    but checked nothing across batches:
    - not the validation sample;
    - not the configuration;
    - not the starting checkpoint;
    - not the sampling seeds.

    The registration's "Reachability" section had checked these by hand, and the report test checks the
    committed pair's hashes.
  - So a later use, such as the report's own suggestion to run "the same probe, started from the promoted
    checkpoint", would pool trials from different checkpoints or samples without a word.
  - A new `poolable(probes)` runs before the analysis in `main()`, and the report test calls it. It refuses two
    batches unless all of these hold:
    - both are identical-config repeatability probes, with equal configurations;
    - their starting checkpoint and config file hash identically (the training code's hashes may differ, as
      `train.py`'s did here);
    - every finished trial, across both, has the same `validation_diag` and prevalence;
    - no sampling seed repeats.
  - As registered, the finished trials of a batch whose later trial failed still count. Each finished trial
    passed the probe's input check at its own end.
- **The analysis is for two batches, and now says so.**
  - `--batch` accepted any number of batches. The shift test and prediction 1 compare the first and the last.
  - `analyse` and `poolable` now refuse anything but two.
- **A first batch with fewer than two finished trials** crashed in `statistics.stdev`. It is now `INSUFFICIENT`,
  like a second batch with fewer than three.
- **Its tests run in the standard suite.**
  - `test_noise_probe_pooled.py` and `test_noise_probe_v3_pooled_report.py` were not in
    `scripts/run_validation_tests.py`. The first probe's report test is in it, and now both of these are too.
  - Ten new tests cover:
    - each refusal: another sample, another prevalence, another configuration, another checkpoint, a repeated
      seed, three batches;
    - the allowed training-code difference;
    - a failed batch's finished trials;
    - a one-trial first batch;
    - the command line refusing before it writes;
    - `LIFT_GATE` against `train.LIFT_MARGIN`.
- **Docs.**
  - `train.py`'s tolerance comment ended "so more probe trials are due". It now gives the pooled result.
  - `docs/REPEATABILITY_PROBE.md` describes pooling.

## Verified, no change needed

- **The committed result is the registered analysis of the committed batches.**
  - The report test re-runs `analyse` and compares it with the JSON. It passes, and `poolable` accepts the pair.
  - Both batches have:
    - equal configurations;
    - the same checkpoint and config hashes;
    - all eight trials on one validation sample (`inputs_sha256` `75e57cf9…`, 97 usable patches) at one prevalence;
    - eight distinct seeds;
    - no `input_error`.
  - Only `train.py`'s hash differs, as the report says.
- **The registration came first.** Commit `70ebcffc` is timed 12:41:19 PT. Batch 2's first trial took 973 s, so
  none could have finished before about 12:57.
- **The numbers.**
  - Pooled SD 0.00286, interval 0.00189–0.00582 (χ², df 7).
  - P(N(0, 2σ²) > 0.01) is 0.67% at the point, 0.009% and 11.2% at the ends.
  - The July tolerance is 0.0066 (0.0044–0.0135).
  - The batch shift is 0.0009 against a Welch SE of 0.0022.
  - Prediction 1's band is 0.2571–0.2723.
  - Each matches the report.
- **Prediction 2 uses the loop's rule.** `val_f1 > incumbent + tolerance` and `ap_lift > 1.02` are
  `train.is_f1_improvement`'s, apart from its finiteness checks. `LIFT_GATE` is now pinned to `train.LIFT_MARGIN`.
- **The report's reading.** The 0.67% compares two draws of one configuration from one checkpoint, so it
  describes the loop only once the incumbent's stored score is such a draw. It does not describe today's
  incumbent, which every trial beats by more than 0.01. The report says both.

## Observations for the owner (not changed)

- **With unequal batch sizes, the within-batch SD departs from the registration's wording.** The registration
  says "√(mean of the two batch variances), df 6". The code weights each variance by its degrees of freedom, the
  usual pooled variance, with df = n₁ + n₂ − 2. The two agree for the 4 + 4 that ran. They differ when a batch has
  a failed trial, which the registration allows.
- **The incumbent's score is passed by hand** (`--incumbent 0.249348`). The probe records the starting
  checkpoint's hash, not its stored val_f1. Reading it from the checkpoint would need torch in the analysis.
- **Carried from the tolerance review:**
  - the tracked `best_model.pt` is still scored under protocol v2;
  - the "34 loop cycles" figure rests on sprint logs that are not committed;
  - night cycles are unmeasured.

## Verification

Environment: CPython 3.10 venv, no GPU visible. No scroll data here; the analysis reads only the committed JSON.

- **Tests:** `pytest tests/test_noise_probe_contracts.py tests/test_noise_probe_v3_report.py
  tests/test_noise_probe_pooled.py tests/test_noise_probe_v3_pooled_report.py tests/test_f1_improvement_criterion.py`:
  103 passed.
- **Mutation check** over the full tracked tree, with the bytecode cache cleared. Each mutation fails at least one
  test:
  - each of the five cross-batch checks removed;
  - the training code not exempted;
  - any number of batches accepted, by `poolable` and by `analyse`;
  - no minimum for batch 1;
  - `main` not calling `poolable`;
  - a failed batch refused outright.
- **`poolable`** on the committed pair: accepted.
- **Lint:** Ruff check and format are clean on the changed files.
- **The standard suite:** see the PR.
