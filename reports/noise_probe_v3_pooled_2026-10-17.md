# Pooled v3 noise probe: eight identical trials (2026-10-17)

**Question:** how often does a cycle that changes nothing clear `F1_NOISE_TOLERANCE` = 0.01 under protocol v3?
The owner set 0.01 on 2026-10-17 (#106). The first probe's four trials put σ at 0.0025, with a 95% interval of
0.0014–0.0094 (`noise_probe_v3_2026-10-16.md`). Over that interval, a no-change cycle cleared 0.01 between 0.2% and
23% of the time. The pre-registration (`docs/preregistration/2026-10-17_noise_probe_v3_pooled.md`, committed
before any new trial finished) fixed the analysis and three predictions.

**Method:**
* **The new batch** ran four trials of `scripts/f1_noise_probe.py --config config.json --checkpoint best_model.pt
  --runs 4 --execute`. It ran from the main checkout at `3b22a7ee`, 12:40–13:44 PT, with the loop stopped.
* **Its inputs** hash identically to batch 1's except `scripts/training/train.py` (`19a8bef6` → `c8bf30b3`). That
  file differs only in the `F1_NOISE_TOLERANCE` line and its comment, which no trial reads: the probe isolates each
  trial's checkpoint.
* **Each trial** starts from the incumbent, trains 900 s under its own sampling seed, and is scored on the v3
  sample.
* **The analysis** is `scripts/noise_probe_pooled.py` on `noise_probe_v3_2026-10-16.json` (batch 1) and
  `noise_probe_v3_2026-10-17.json` (batch 2). It writes `noise_probe_v3_pooled_2026-10-17.json`.

## Result

Batch 2:

| trial | sampling seed | val_f1 | ROC AUC | AP lift |
|---|---:|---:|---:|---:|
| 1 | 1317204322 | 0.2689 | 0.5806 | 1.201 |
| 2 | 2038636696 | 0.2607 | 0.5725 | 1.170 |
| 3 | 495948656 | 0.2655 | 0.5782 | 1.209 |
| 4 | 113474145 | 0.2670 | 0.5813 | 1.208 |

**All eight trials pooled: mean 0.2651, SD 0.0029 (df 7), 95% interval 0.0019–0.0058.** Batch 1 alone put the
interval's top at 0.0094.

* **No shift between batches:** batch means 0.2647 and 0.2655, difference 0.0009 against a Welch SE of 0.0022,
  well under the registered 2 SE. So the pooled SD leads. The within-batch estimate agrees: 0.0030
  (0.0020–0.0067, df 6).
* **False promotion at 0.01**, the rate at which a no-change cycle clears it: 0.67% at the point estimate, 0.009% at
  the interval's low end and 11.2% at its high end. The point rate is under the 5% the July derivation
  aimed for, but the high end is above it.
* **The July formula's tolerance**, 1.645 × √2 × σ, is 0.0066 (0.0044–0.0135). So 0.01 lies inside the range the
  formula gives over σ's interval.
* **Predictions: all three held.**
  * **P1:** every batch-2 trial lies in batch 1's mean ± 3 SD band 0.2571–0.2723; batch 2 spans 0.2607–0.2689.
  * **P2:** all four would be promoted under 0.01. Each is above 0.2593, with AP lifts 1.170–1.209 against the 1.02
    gate.
  * **P3:** the pooled SD, 0.0029, is at most 0.0043.

## What the rate does and does not describe

* **The 0.67% compares two scores of the same configuration, trained from the same checkpoint.** It describes the
  loop once the incumbent's stored val_f1 is itself the score of such a cycle.
* **Today's stored score is not.** The stored 0.2493 is `best_model.pt`'s own score.
  * Every trial beats it by 0.011 to 0.020 (mean 0.0158, 5.5 pooled SDs), so 8 of 8 would be promoted.
  * By val_f1, so would all 34 loop cycles scored under v3 on 10-16/17, which beat it by 0.011–0.022 (#106).
  * The first cycle to finish under 0.01 is therefore very likely to promote, whatever it changed.
* **After that promotion, the rate is unmeasured.** It depends on what one more 900 s cycle adds to the promoted
  checkpoint. It added about 0.016 to `best_model.pt`. The first probe could not say whether that was a recipe gain
  or the incumbent's one-time adaptation to per-run crops (#79). If later cycles keep adding, no-change cycles keep
  promoting above the 0.67% rate. The same probe, started from the promoted checkpoint, would measure that rate.
* **It does not set the tolerance.** The probe never calibrates it (`tolerance_calibrated: false`). The tolerance
  stays the owner's call.
* **n = 8.** σ's interval still spans a factor of 3.1. All eight trials start from one checkpoint, so the spread
  from any other starting checkpoint is unmeasured.
