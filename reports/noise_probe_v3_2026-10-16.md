# Identical-config F1 noise probe under protocol v3 (2026-10-16)

**Question:** how far apart do four identical loop cycles land on the v3 validation sample? The promotion tolerance,
0.03, came from the 2026-07-12 probe, run under protocol v1 at val_f1 ≈ 0.45 (`reports/detector/f1_noise_probe.md`).
Protocol v3 (#66) scores all 400 patches of the seeded draw, ink-free ones included. It puts the incumbent at
0.2493, against an all-ink baseline of 0.2451.

**Method:** step 3 of #66's post-merge flow, with the loop paused:
* `scripts/f1_noise_probe.py --config config.json --checkpoint best_model.pt --runs 4 --execute`;
* main `c927cee7`, with #74 (loader workers), #75 (GPU Frangi) and #79 (per-run training crops) merged;
* each trial starts from the incumbent, trains 900 s under its own sampling seed, and is scored on the v3 sample.

The first attempt died in 47 s ("AF_UNIX path too long", #98). These trials ran from #98's branch, whose `train.py`
and trial runner hash identically to main's (`input_hashes` in the JSON). Raw results:
`noise_probe_v3_2026-10-16.json`.

## Result

| trial | sampling seed | val_f1 | ROC AUC | AP lift | throughput (Mvox/s) |
|---|---:|---:|---:|---:|---:|
| 1 | 978316533 | 0.2669 | 0.5818 | 1.203 | 0.67 |
| 2 | 732128069 | 0.2665 | 0.5826 | 1.230 | 0.70 |
| 3 | 1176016098 | 0.2615 | 0.5753 | 1.176 | 0.72 |
| 4 | 893960969 | 0.2639 | 0.5698 | 1.168 | 0.74 |

**n = 4, mean 0.2647, sample SD 0.0025, range 0.0054.** With 3 degrees of freedom, the 95% interval for σ is
0.0014–0.0094.

* **Every trial beats the incumbent** (0.2493) by 0.012 to 0.018, which is 4.8 to 6.9 SDs. The incumbent itself is
  ROC AUC 0.5717, AP lift 1.144.
* **None would be promoted.** The rule (`is_f1_improvement`) needs val_f1 above the stored 0.2493 by more than
  `F1_NOISE_TOLERANCE` = 0.03, so above 0.2793. All four AP lifts clear its 1.02 gate.
* **The tolerance, re-derived.** The July derivation is 1.645 × √2 × σ, for a ~5% false-promotion rate. On this
  σ it gives 0.0059. The ends of σ's interval give 0.0033 and 0.022, and even the high end is below 0.03.
* **Throughput** is 0.67–0.74 Mvox/s, or 2,300–2,530 steps in 900 s. Frangi cycles on the 10-14 code had a median
  of 0.31 over 57 cycles (10-15/16), about 1,060 steps. That is the first GPU measurement of #74 and #75 together:
  2.2–2.4× faster.

## What it does not say

* **It does not set the tolerance.** The probe records spread and never calibrates it (`tolerance_calibrated:
  false`). Changing `F1_NOISE_TOLERANCE` is the owner's decision.
  * **Decision, 2026-10-17:** the owner set `F1_NOISE_TOLERANCE` to 0.01, so promotion now needs val_f1 above 0.2593.
    All four trials clear it.
* **It does not show the loop has found a lever.** All four trials start from the same incumbent and differ only in
  seed. The +0.015 they share is what one 900 s cycle of the merged recipe (#74, #75, #79: new crops, about twice
  the steps) adds to the incumbent. That can be a recipe gain or the incumbent's own one-time adaptation to
  per-run crops; this probe cannot separate them.
* **n = 4.** The σ interval spans a factor of 6.6.
