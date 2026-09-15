# Averaging seeds buys exactly what independent-noise theory predicts

**2026-09-15.** Registered in `docs/preregistration/2026-09-14_consensus_retest_calibrated.md`, decided
by `scripts/analyse_consensus_retest.py`. `reports/consensus_retest_verdict.json`.

**The analysis ran unattended.** The decision rule, the validity gate and the retirement of the
A-vs-B comparison were all committed before triplet C existed, and the run was triggered by a waiter
when the last arm scored. Nobody sat between seeing a number and deciding what it meant.

## Result

| comparison | r | predicted | verdict |
|---|---:|---:|---|
| **A vs C** | **0.875** | 0.877 | CONFIRMED |
| **B vs C** | **0.893** | 0.877 | CONFIRMED |

**VERDICT: CONFIRMED.** Both land in the registered 0.85–0.91 band. The prediction was fixed at
**0.877** from the independent-noise model `r_k = 1/(1 + ratio/k)` with `ratio = 0.4205` derived from
`r_single = 0.7040` over all 15 pairs of `s1–s6`.

So a **3-seed consensus reproduces at r ≈ 0.88** where a single fit reproduces at **0.70**. Averaging
recovers what the model says it should, on arms that did not exist when the number was written down.

## Controls, all passed

* **Non-blank strip fraction**, registered band 0.40–0.55: `s7` 48.2%, `s8` 45.6%, `s9` 47.1%.
* **Validity gate** on `total_fg_pixels`, 95% PI from `s1–s6` (2,398,918–3,639,084): all nine arms
  inside, `s7` at 2,974,987, `s8` 2,881,173, `s9` 2,818,864.
* **A-vs-B stayed retired.** It was seen at 0.876 before this registration existed and the module
  refuses to compute it, so the confirmation rests only on comparisons that did not exist when the
  prediction was fixed.

## The two comparisons agree, and their small difference points the right way

A-vs-C is **0.018 lower** than B-vs-C, and that is the direction the registered confound predicts:
triplet A rendered from `d8c5f488a` while B and C are on `be09a8503`, whereas B-vs-C is
render-clean. The third amendment bounded that confound at **r = 0.9715 between the same fit rendered
on the two trees**, i.e. a decorrelation of 0.0285 against 0.2822 for a reseed — small, and of about
the size seen here.

That is a consistency check, not a new finding, and it is worth being explicit: had the two
comparisons disagreed, the registered verdict was INCONSISTENT and **neither would have been
claimed**. They agree, so the confound does not have to be adjudicated.

## What this licenses

**A loop that already runs two seeds should keep the consensus rather than the winner.** The gain is
real, predictable in advance, and costs nothing beyond the fits already being run. Three seeds reach
0.88; two reach **0.8516, since measured directly** (`reports/two_seed_consensus_confirmed.md`) rather
than projected — the model predicted 0.826 for that case and slightly under-predicted it.

## What it does not license

* **This is reproducibility, not accuracy.** Two fits agreeing more closely says nothing about either
  being right. The consensus is more stable, not more correct.
* **Thresholding remains refuted.** `reports/confidence_predicts_but_thresholding_does_not_help.md`
  showed that at matched sparsity, top-confidence ink is *worse* than a random selection of the same
  size. Averaging is the lever; confidence filtering is not.
* **It does not extend past k = 3.** The model predicts further gains, but nothing here measures them.
* **The instability itself is unexplained.** Placement reproduces at 0.70 between seeds while the
  count reproduces to 1.2%, and the mechanism is still unknown after two failed tests. This result
  tells you how to live with that, not why it happens.
