# Pre-registration: do same-winding constraints buy reading? Three more ablated seeds

**Written 2026-09-28, before any of the three new fits was started.** Decision code:
`scripts/analyse_samewinding_extension.py`, committed with this file.

## Why

The September filing says the same-winding ablation "bounds what winding constraints buy for reading".
`reports/control_sensitivity.md` (09-27) showed that the bound on what they *buy* is the lower end of
the removal effect's interval. That end depends on the control seeds: −2.56% with the three registered
seeds, −7.98% with all nine, and −12.18% with the six render-matched ones. The ablated arm has only
three seeds, so this question is limited by the ablated side.

## Design

Three new ablated fits, `nosamecur_s4`, `s5` and `s6`. Each is byte-identical to `fit_nosamecur_s1-s3.sh`
apart from `optimizer_random_seed` (4, 5, 6) and the tag:

* dataset `data/spiral_s1_nosamewind`, whose `same_windings.json` holds no collections;
* fitted from `villa-spiral-current`, the unchanged `d8c5f488a` copy every current-tier fit used;
* 30,000 steps, z 13056–18432, fibers, tracks and drawn control points off, as before.

They are rendered and scored by `repro/spiral_render/run_arm_sequence.sh` with **`VILLA_REF` pinned to
`be09a8503`**. That is the render tree `curbase_s7-s9` recorded, and it holds the same versions of all
19 d8c5→be09 files as every other render-matched arm (`reports/villa_copy_tree.txt`). The flatten is
the stock stochastic flatten, as for every arm compared here.

## Validity gates (each new arm; a failing arm is re-rendered, never dropped)

1. `VILLA_SHA` equals `be09a85035059fd83471b1632b5898c62f2c65b1`.
2. `inkdelta check`, run against the arm's sequence log, reports no FAIL: no stale slices, no all-zero
   strip, no zero score.
3. Strip area (`total_pixels`) is within ±5% of the `curbase_s4-s9` mean.

## Analysis (inkdelta 0.3.0, `--cv 0.0536` as floor, alpha 0.05)

| | control | ablated | role |
|---|---|---|---|
| **primary** | `curbase_s4-s9` (render-matched) | `nosamecur_s1-s6` | decides |
| secondary | `curbase_s1-s9` | `nosamecur_s1-s6` | reported |
| replication | `curbase_s4-s9` | `nosamecur_s4-s6` only | reported |

Rule on the primary comparison:

* **RESOLVED (−)** → CONSTRAINTS BUY READING, with the effect and interval;
* **RESOLVED (+)** → REMOVING THEM HELPS;
* **NOT RESOLVED** → NULL. The registered statement is then "same-winding constraints buy at most
  X% of reading", where X is minus the interval's lower end.

The floor is 0.0536 (current tier, df 11, CI [0.0380, 0.0911]). With it the primary comparison's
smallest interval half-width is 1.96 × 0.0536 × √(1/6 + 1/6) = **6.1%**. That is the best bound this
design can give, and it holds only if the replicates are no noisier than the floor.

## Prediction, blind

**NULL.** Point estimate between −1% and −5%, and a lower bound between −6% and −10%, so "buy at most
~6–10%". I will be wrong if the new seeds land near the old nosamecur triplet (+0.28% vs s1-s3, mean
2,890,443): then the point moves toward −3%. Or I will be wrong if they resolve a loss.

## What it cannot do

It answers for one ROI, one dataset and w120–w129. `total_fg_pixels` is a count, not legibility. The
control and ablated arms were fitted days apart on the same code, and they are rendered on the same
render tree only for the 19 files checked plus the pin.

## Cost

Three fits (~3 h each) and three renders plus scores (~3 h each), serial: ~18 h on the RTX 4090. The
box is otherwise idle.
