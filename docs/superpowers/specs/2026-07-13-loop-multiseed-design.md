# Loop multi-seed cycles — design note

**Date:** 2026-07-13
**Status:** design, NOT implemented (loop is paused per the Q3 strategy; resuming is a
separate decision). This note makes the capability ready to build when the loop is resumed.

## Problem

The identical-config noise probe (`reports/detector/f1_noise_probe.md`, 2026-07-12)
measured true run-to-run `val_f1` σ = 0.0120 at the 900s day-shift budget. A single-run
promotion compares two noisy draws (σ_diff = √2·σ ≈ 0.017), so even the calibrated
`F1_NOISE_TOLERANCE = 3e-2` only holds the false-promotion rate near ~5% — and, more
importantly, **at 900s no sampled tweak separates from noise** (the cycle-9 "+0.0137" was
0.8·σ_diff). The loop's search is currently noise-dominated: it cannot detect a real tweak
effect smaller than ~0.03 in `val_f1`, which is larger than any effect observed.

## Options (measured trade-offs)

| lever | effect on the noise floor | cost |
|---|---|---|
| Wider tolerance (current: 3e-2) | rare, honest promotions; can't see small gains | none (done) |
| **Multi-seed cycles (k runs, average)** | σ_mean = σ/√k → k=3 gives σ ≈ 0.0069, σ_diff ≈ 0.0098, 5% tolerance ≈ 0.016 | k× GPU per cycle |
| Longer budget per cycle | lowers σ (more convergence) by an unknown amount | proportional GPU; fewer cycles/day |

Multi-seed is the principled fix: it directly shrinks the promotion noise floor with a known
√k law, letting the loop detect ~0.016-scale effects at k=3 instead of ~0.03.

## Design (opt-in; default behavior unchanged)

Implement at the **loop level** (`run_autoresearch_loop.py`), reusing the existing
non-destructive `checkpoint_out` path in `train.py` (which trains + evaluates + writes
`run_result.json` but does NOT touch `best_model.pt`/history/results):

1. New config field `multi_seed_k: int = 1` (1 = today's behavior, no change).
2. Per cycle, if `k > 1`: run the candidate config `k` times via `train.py --config <tmp>`
   with distinct `seed` values and `checkpoint_out=/tmp/cycle_seed_i.pt` (isolated). Collect
   the `k` `val_f1` (+ `ap_prevalence_lift`) from each run's `run_result.json`.
3. Promotion decision uses the **mean** `val_f1` and the **min** `ap_prevalence_lift`
   (fail-closed on the lift gate) against `best_val_f1 + F1_NOISE_TOLERANCE`, with the
   tolerance narrowed to reflect σ/√k (e.g. `F1_NOISE_TOLERANCE / sqrt(k)` or a separate
   `multi_seed_tolerance`).
4. On promotion, do ONE final non-isolated run (or keep the best-of-k checkpoint) to update
   `best_model.pt`. Record all k `val_f1` in the sprint log for auditability.

`train.py`'s `seed` is already a config field and eval is fixed-seed; only the **training**
dataloader is unseeded, so distinct `seed`s give the independent draws we need. No change to
the honest-metric selection logic itself.

## Why not now

- The loop is paused; the Q3 strategy assigns GPU to benchmark work.
- k× GPU per cycle is a real cost that only pays off once the search is worth running at all
  (i.e. once there is a regime with signal — the 64px prize window is at chance on this data).
- `run_autoresearch_loop.py` is also touched by the parallel agent; a core change there
  should be coordinated, not slipped in while paused.

## Recommendation

Keep as designed-not-built. Implement only alongside a decision to resume the loop AND a
regime change that could plausibly carry signal (e.g. a different data source), since
multi-seed sharpens detection but does not create signal that the prize-legal window lacks.
See [[loop-selects-on-honest-f1]] and the noise probe report.
