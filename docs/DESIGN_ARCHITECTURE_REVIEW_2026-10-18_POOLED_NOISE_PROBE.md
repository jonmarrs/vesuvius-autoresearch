# Design and architecture review — the pooled v3 noise probe (#109)

Date: 2026-10-18. Baseline: `0580e5a7` (main after #114). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #109 (merged as `f85e0f7d`):
- the pre-registration `docs/preregistration/2026-10-17_noise_probe_v3_pooled.md`;
- the analysis `scripts/noise_probe_pooled.py`;
- its result `reports/noise_probe_v3_pooled_2026-10-17.{json,md}`, and batch 2's
  `reports/noise_probe_v3_2026-10-17.json`;
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
    - not the code;
    - not the sampling seeds.

    The registration's "Reachability" section had checked these by hand for this pair, and the report test
    checks the pair's hashes. Any later pooling had no check that two batches were draws of one comparison.
  - A new `poolable(probes, allow_code)` runs before the analysis in `main()`, and the report test calls it. It
    refuses two batches unless all of these hold:
    - both are identical-config repeatability probes, under one probe contract, with equal configurations;
    - the starting checkpoint and config file hash identically, and both hashes are present;
    - the probe runner and the trainer hash identically, unless the difference is named. The registration names
      one difference, `train.py`'s, and says why no trial reads it. So the committed result now needs
      `--allow-code-change scripts/training/train.py`, and gives the same JSON byte for byte with it.
    - every finished trial, across both batches, records a validation sample (a non-empty `inputs_sha256` and a
      finite prevalence), and all are the same one;
    - no sampling seed repeats.
  - As registered, the finished trials of a batch whose later trial failed still count. Each finished trial
    passed the probe's input check at its own end.
  - A refusal exits 2 with the reasons and writes nothing. `INSUFFICIENT` still writes its JSON and exits 1.
- **The analysis is for two batches, and now says so.**
  - `--batch` accepted any number of batches. The shift test and prediction 1 compare the first and the last.
  - `analyse` and `poolable` now refuse anything but two.
- **A first batch with fewer than two finished trials** crashed in `statistics.stdev`. It is now `INSUFFICIENT`,
  like a second batch with fewer than three.
- **Its tests run in the standard suite.**
  - `test_noise_probe_pooled.py` and `test_noise_probe_v3_pooled_report.py` were not in
    `scripts/run_validation_tests.py`. The first probe's report test is in it, and now both of these are too.
  - New tests cover:
    - each refusal;
    - a batch whose trials agree with each other but not with the other batch, on `inputs_sha256`, usable
      patches or prevalence;
    - trials that record no sample;
    - a code difference, refused until named;
    - a failed record as the probe writes it, without metrics;
    - the command line refusing before it writes, and reproducing the committed result;
    - `LIFT_GATE` against `train.LIFT_MARGIN`.
- **Docs.**
  - `train.py`'s tolerance comment says "so more probe trials are due"; a line after its parenthetical now gives
    the pooled result. `docs/REPEATABILITY_PROBE.md` describes pooling.

## Verified, no change needed

- **The committed result is the registered analysis of the committed batches.**
  - The report test re-runs `analyse` and compares it with the JSON. The command line, with the named `train.py`
    difference, writes the same file byte for byte.
  - Both batches have:
    - equal configurations;
    - the same checkpoint and config hashes;
    - all eight trials on one validation sample (`inputs_sha256` `75e57cf9…`, 97 usable patches) at one prevalence;
    - eight distinct seeds;
    - no `input_error`.
  - Of the hashed inputs, only `train.py` differs, as the report says (`19a8bef6` → `c8bf30b3`, a comment and the
    constant).
- **The registration's timing.**
  - Commit `70ebcffc` is timed 12:41:19 PT.
  - Batch 2's first trial took 973 s, so given the registered 12:40 launch it finished at about 12:56.
  - The probe records durations, not times, so the launch time is the owner's statement.
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

- **The two batches ran on differently pinned villa commits, and the probe does not hash villa.**
  - Batch 1's `train.py` hash (`19a8bef6`) is that of `c927cee7` and `64fff5bf`, which pin `9afddaf0`. Batch 2
    ran at `3b22a7ee`, which pins `ccb43181`, after the bump in `a0093a2b` (20 upstream commits).
  - Which villa checkout each trial actually ran on is not recorded.
  - Of the villa code the trainer imports, `segmentation/` and `ink-detection/` are unchanged between the two
    pins, as are the `vesuvius.models` and `vesuvius.image_proc` modules it names. In those packages only
    `models/configuration/config_manager.py` changed, and none of the trainer's direct imports names it.
  - Transitive imports were not traced.
- **With unequal batch sizes, the within-batch SD departs from the registration's wording.**
  - The registration says "√(mean of the two batch variances), df 6".
  - The code weights each variance by its degrees of freedom, the usual pooled variance, with
    df = n₁ + n₂ − 2.
  - The two agree for the 4 + 4 that ran. They differ when a batch has a failed trial, which the registration
    allows: for 4 + 3 trials, df is 5.
- **An interrupted batch's finished trials count too.** The registration speaks of failed trials. An interruption
  is a person's decision, which can depend on the scores seen so far.
- **The committed JSON does not record the allowed code difference.** The source batches' hashes and the report
  do. Adding it would change the owner's committed result.
- **The incumbent's score is passed by hand** (`--incumbent 0.249348`). The probe records the starting
  checkpoint's hash, not its stored val_f1.
- **Carried from the tolerance review:**
  - the tracked `best_model.pt` is still scored under protocol v2;
  - the "34 loop cycles" figure rests on sprint logs that are not committed;
  - night cycles are unmeasured.

## Verification

Environment: CPython 3.10 venv, no GPU visible. No scroll data here; the analysis reads only the committed JSON.

- **Tests:** `pytest tests/test_noise_probe_contracts.py tests/test_noise_probe_v3_report.py
  tests/test_noise_probe_pooled.py tests/test_noise_probe_v3_pooled_report.py
  tests/test_f1_improvement_criterion.py`: 114 passed.
- **Mutation check** over the full tracked tree, with the bytecode cache cleared. Each of these mutations fails at
  least one test:
  - the scope, contract, configuration, checkpoint-and-config, code, sample and seed checks, each removed;
  - the sample compared only within each batch;
  - `inputs_sha256` dropped from the sample;
  - missing evidence accepted;
  - failed records included in the cross-trial checks;
  - a missing code hash accepted;
  - code matched without a path boundary;
  - any number of batches accepted;
  - no minimum for batch 1;
  - `main` not calling `poolable`, or not catching its refusal;
  - a failed batch refused outright.
- **The command line:** without `--allow-code-change` it refuses the committed pair (exit 2, no file). With it,
  it writes the committed JSON byte for byte.
- **Lint:** Ruff check and format are clean on the changed files.
- **Independent review** of the first commit found:
  - the code exemption broader than the registration, and unrecorded;
  - tests that varied one trial, so a check within a batch passed them;
  - six surviving mutations;
  - the seed check described as the probe's;
  - the registration's timing overstated;
  - the villa pin difference;
  - several smaller points.

  All are addressed above.
- **The standard suite:** see the PR.
