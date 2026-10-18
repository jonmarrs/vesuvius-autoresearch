# Pre-registration: how often does a no-change cycle clear the 0.01 tolerance under protocol v3?

**Written 2026-10-17 12:41 PT, after the four new trials were launched (12:40) and before any of them finished.**

## The question

On 2026-10-17 the owner lowered `F1_NOISE_TOLERANCE` from 0.03 to 0.01 (#106). The first v3 probe
(`reports/noise_probe_v3_2026-10-16.md`, 4 trials) put the run-to-run σ at 0.0025, with a 95% interval of
0.0014–0.0094. Across that interval, a cycle that changes nothing clears 0.01 between 0.2% and 23% of the
time. Four more identical trials, pooled with the first four, narrow σ. The result tells the owner whether
0.01 holds the false-promotion rate near the ~5% the July derivation aimed for.

## Reachability

* **Same configuration.** The dry-run plan's `config` equals the first probe's (`local_data/noise_probe_v3_2026-10-16b/probe.json`).
* **Same checkpoint and data hashes.**
* **Same protocol** (`seeded-sample-400-v3+z1-27`).
* **One training-code difference, which no trial reads.** `scripts/training/train.py` differs from the
  first probe's (sha256 `19a8bef6…`, `c927cee7`) only in the `F1_NOISE_TOLERANCE` line and its comment. A
  probe trial never promotes: the probe isolates each trial's checkpoint.
* **Different seeds.** Each trial draws its own `train_sampling_seed` (#79), so the new trials are not
  replays of the first four.

## The floor

This study measures it. σ is the sample SD of the trials' val_f1, and its interval comes from χ²:
* df 7 for the pooled eight trials;
* df 6 for the within-batch estimate below.

## Arms

| arm | work dir | trials |
|---|---|---|
| batch 1 | `local_data/noise_probe_v3_2026-10-16b` | 4, run 2026-10-16 from the #98 worktree |
| batch 2 | `local_data/noise_probe_v3_2026-10-17` | 4, run 2026-10-17 from the main checkout at `3b22a7ee` |

Both batches start from `best_model.pt` (stored val_f1 0.249348), use `config.json`, run 900 s, and run
with the loop stopped.

## Predictions, fixed now

1. **Each batch-2 trial lies within 0.2647 ± 0.0075**, batch 1's mean ± 3 × its SD.
2. **All four batch-2 trials would be promoted under 0.01**: val_f1 above 0.2593, and AP lift above 1.02.
3. **The pooled σ (df 7) is at most 0.0043**, the σ at which 0.01 gives a 5% false-promotion rate.

## Analysis, fixed now

* **Pooled σ.** The sample SD of all eight val_f1 values, with its χ² 95% interval at df 7.
* **Batch shift.** The difference of batch means, with its Welch SE.
  * If |difference| > 2 SE, a shift between batches inflates the pooled SD.
  * In that case the report leads with the within-batch σ: √(mean of the two batch variances), df 6.
* **False-promotion rate at 0.01.** P(N(0, 2σ²) > 0.01), at the point estimate and at both ends of the
  interval.
* **The tolerance the July formula gives**, 1.645 × √2 × σ, at the same three points.

## What changes

The tolerance is the owner's call; the report states the rates and recommends nothing beyond them. If
the point estimate's rate is above 5%, the report says so first.

## Failure handling

* **A trial that fails** is reported and not replaced.
* **Fewer than 3 completed batch-2 trials:** the pooled analysis is not run.
