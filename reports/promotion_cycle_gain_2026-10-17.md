# After the first promotion under 0.01, the cycle's gain is gone (2026-10-17)

**Question.** `docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-17_TOLERANCE.md` suggests a test of the cycle effect: watch
whether the margin after the first promotion falls to the noise. Every v3 cycle before the promotion beat the stored
incumbent by about 0.016. Is the margin still there?

**Source.** The loop's console log, `autoresearch.out`, which is not committed. A cycle's incumbent is the "best was"
of its verdict line. `scripts/promotion_cycle_gain.py` reads the log from the first start-up on the v3 incumbent
(0.249348) and writes every cycle to `promotion_cycle_gain_2026-10-17.json`. The first promotion under 0.01 was
`batch_size_8` (0.2658), at 14:01. The log runs through `weight_decay_0.0`, before the 10-17 night shift.

**This is descriptive, not pre-registered.** I had seen cycles 2–9 after the promotion before writing it.

## Result

| incumbent faced | cycles scored | mean gain | SD | range | clear 0.01 |
|---:|---:|---:|---:|---:|---:|
| 0.2493 | 50 | +0.0157 | 0.0034 | -0.0002 to +0.0245 | 49 |
| 0.2658 | 17 | -0.0004 | 0.0031 | -0.0044 to +0.0057 | 0 |

* **Before the promotion, 49 of the 50 scored cycles cleared 0.01.**
  * One more cycle, a 60-minute `use_uamt_False`, was killed at its timeout and has no score.
  * The one under 0.01 is `lr_1e-05` (-0.0002), the lowest learning rate the loop tried. Finding 88's part D had
    the same exception: its two `lr` 1e-4 candidates were the only ones under 0.01. The gain went with how far a
    cycle moved the incumbent.
  * 15-minute cycles gained +0.0155 (n = 39) and 60-minute cycles gained +0.0164 (n = 11).
* **After it, the margin is at the noise.**
  * The mean gain is -0.0004, no cycle clears 0.01, and the best is `aug_mode_batchgeneratorsv2` at +0.0057.
  * Each of the 17 cycles applied a different tweak. Their SD 0.0031 lies inside the interval for identical cycles,
    0.0029 (0.0019–0.0058), that the pooled noise probe measured (#109). So no tweak's effect stands out from
    run-to-run noise.
  * Within one SD, their mean val_f1, 0.2654, is the probe's mean, 0.2651. A cycle from the promoted checkpoint lands
    where a cycle from the old one did: the extra 15 minutes of training in the incumbent added nothing measurable.
* **What this means for the loop.** The first promotion absorbed the one-time gain the review predicted. The stored
  score now sits near its own configuration's mean, which is the premise of #109's 0.67% false-promotion rate. So a
  tweak now has to be worth about 0.01 to promote, and none of these 17 comes close.

## What it does not say

* **The tweaks' effects are small, not shown to be zero.** Different tweaks spreading like identical cycles bounds
  their effects against the noise. It does not measure any one of them.
* **The σ comes from the old checkpoint.** Both probes started from `best_model.pt` as re-scored on 10-16. The
  spread from the promoted checkpoint is unmeasured: the same probe, started from it, would measure it (GPU, the
  owner's call).
* **All 17 cycles after the promotion ran 15 minutes.** The 60-minute cycles start with the 10-17 night shift.
