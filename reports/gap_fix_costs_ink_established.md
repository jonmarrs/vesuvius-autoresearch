# ESTABLISHED: the gap-expander change costs ~10% of recovered ink while improving the geometry score

**2026-09-03.** Second look, registered in `docs/preregistration/2026-09-02_gap_ink_second_look.md`
with `scripts/analyse_gap_ink_second_look.py` committed before any of the five new fits started.
**Registered prediction MET.** Finding 13, open since 2026-09-01, resolves.

## Result

`total_fg_pixels`, Welch two-sided, 6 vs 6, tested at the **Pocock alpha = 0.0294** for a second look:

```
BASE mean 1,719,984      GAP mean 1,541,596
rel -10.35%,  95% CI -15.68% to -5.03%,  t = -4.404, df = 8.89,  p = 0.0018
```

**p = 0.0018 clears 0.0294 by more than an order of magnitude. The effect is established.**

| fit | arm | `satisfied_area` | `total_fg_pixels` |
|---|---|---:|---:|
| baseline01 | BASE | 0.8398 | 1,789,206 |
| seed02 | BASE | 0.8404 | 1,732,741 |
| seed03 | BASE | 0.8382 | 1,620,364 |
| seed04 | BASE | 0.8399 | 1,682,825 |
| seed05 | BASE | 0.8396 | 1,658,297 |
| seed06 | BASE | 0.8359 | 1,834,470 |
| gap133 | GAP | 0.8480 | 1,591,857 |
| gap133s2 | GAP | 0.8465 | 1,604,683 |
| gap133s3 | GAP | 0.8489 | 1,448,920 |
| gap133s4 | GAP | 0.8466 | 1,527,554 |
| gap133s5 | GAP | 0.8482 | 1,554,826 |
| gap133s6 | GAP | 0.8481 | 1,521,735 |

Both registered quality gates passed and were applied per arm, never pooled: BASE `satisfied_area`
spread 0.0045, GAP 0.0024, both inside the 0.01 band.

The confirmatory check agrees, and is still subordinate by registration: **complete separation**, all
six GAP fits below all six BASE fits, null probability **0.108%**.

`overall_fg_fraction` moves with it (-10.78%, p = 0.0015), so the result is not an artefact of strip
area. `line` (-0.38%, p = 0.84) and `column` (-12.53%, p = 0.23) are not established.

## What this means, and it is not what I expected

**The same one-line change improves villa's geometry diagnostic and degrades its ink objective.**
`satisfied_area` rises 0.83897 -> 0.84764 (p = 3.9e-06, completely disjoint) while `total_fg_pixels`
falls 10.35% (p = 0.0018, completely disjoint). Both directions are established on the same twelve
fits, by the same seeds, at the same time.

That sharpens finding 10 considerably. Finding 10 said geometry and ink *decouple* at seed scale —
that a better `satisfied_area` does not imply more ink. This is stronger: for this change they move
in **opposite** directions, and both moves are individually significant.

**The consequence for a loop that optimises ink with a satisfaction cross-check is direct.**
`autoresearch.md` prescribes exactly that arrangement. Here the cross-check would have *passed
enthusiastically* — satisfaction up 7 to 10 sd — on a change that costs a tenth of the objective. A
guard that fires in the wrong direction is worse than no guard, because it converts a real regression
into an apparent double win.

## Scope, which is narrower than the numbers suggest

**This is not a live villa defect.** The fits ran on `villa-spiral`'s working tree at `6847063f`
(2026-08-26), which predates upstream's `61a62c445` (#1625, 2026-08-27). On that tree
`model_gap_expander_num_windings` really did allocate the gap lattice through the `transforms.py`
fallback, and 130 was below the `shell_outer_winding_idx + 3 = 133` the code demanded. Upstream has
since split the parameter and defaulted the capacity to 144, so the shortfall no longer exists.
See `reports/gap_expander_finding_is_stale_upstream_fixed_it.md`.

So the finding is about the **metrics**, not the config: a change that genuinely improved the fit's
geometry cost ink, on this scroll, in this region.

## Limits

One dataset, one ROI, one winding decade (w120-w129), one architecture, twelve fits differing only in
seed and one config flag. The renders span three days on one machine; `gap133s2` was rendered twice
after an OOM kill. Nothing here says the change costs ink on the inner windings, which were never
measured for it, nor that the direction generalises to other config changes — finding 10's decoupling
already implies it need not.

**Exploratory, not claimed:** within each arm `corr(satisfied_area, total_fg_pixels)` is -0.40 (BASE)
and -0.59 (GAP), n=6 each, where a correlation is near-uninformative. The pooled -0.85 is driven by
the between-arm difference and is not additional evidence. A within-fit anti-correlation would be a
much stronger claim than this arm can support, and is not made.

## Provenance

Fits: `villa-spiral` working tree `6847063f`. Renders and scoring: its `origin/main` `5479453a`.
Two refs, one pipeline — every arm shares both, which is what the comparison requires.
