# Identical-config F1 noise probe (2026-07-12)

**Question:** what is the TRUE run-to-run val_f1 noise of a loop cycle, measured on
identical configs (no tweak variance)? The 2026-07-11 estimate (std 0.0095) came from
REVERTED cycles with *different* tweaks and was assumed to be an upper bound.

**Method:** 4 sequential runs of the promoted config (`use_uamt`, 900s budget) via
`scripts/f1_noise_probe.py`, each isolated with `checkpoint_out` (cannot touch
`best_model.pt`/`history.tsv`/`results.tsv`/`prize_readiness.tsv`). Training dataloader
is unseeded (true stochasticity); eval is fixed-seed (deterministic scoring). Raw
results: `f1_noise_probe.json`.

## Result

| run | val_f1 | ap_lift |
|---|---|---|
| 1 | 0.4362 | 1.210 |
| 2 | 0.4623 | 1.365 |
| 3 | 0.4554 | 1.300 |
| 4 | 0.4423 | 1.284 |

**n=4, mean 0.4491, std 0.0120, range 0.0262.**

## Implications (each applied)

1. **The "upper bound" understated the truth.** True identical-config σ (0.0120) exceeds
   the cross-tweak spread (0.0095) — tweak effects at this budget are negligible relative
   to training noise.
2. **Tolerance recalibrated 1e-2 → 3e-2.** A promotion compares two noisy draws
   (σ_diff = √2·σ ≈ 0.017); at tol 0.01 a no-effect tweak false-promotes ≈28% of the
   time; ≈5% requires 1.645·σ_diff ≈ 0.028. Applied in `scripts/training/train.py`.
3. **The 2026-07-11 cycle-9 promotion (+0.0137, `use_uamt`) was noise** (0.8 σ_diff).
   `best_model.pt` retains that checkpoint (statistically indistinguishable from its
   baseline, not worse), but the "improvement" claim is retracted here.
4. **The deeper conclusion:** at the 900s day-shift budget, the honest metric shows the
   loop's entire tweak search is noise-dominated — no sampled tweak separates from σ.
   For the loop to be scientifically meaningful at resume it needs either the wide
   tolerance (rare, honest promotions) or per-cycle multi-seed averaging
   (σ_mean = σ/√k; k=3 brings the 5% tolerance to ≈0.016), or longer budgets.
   This measurement is itself the honest-metrics contract working as designed.
