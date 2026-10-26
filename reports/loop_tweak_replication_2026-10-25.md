# One tweak beats the others on every cycle it ran, and the loop's rule cannot promote it (2026-10-25)

**Question.** The loop has not promoted since `batch_size_8` (0.265762) on 2026-10-17. #112 found the 17 cycles after
that promotion at the noise, but each was a different tweak. Since then every tweak has recurred, 11 to 28 times. Does
any of them beat the others reproducibly?

**Source.** The loop's sprint logs and its run logs (`run.log.old`, `run.log`), which are not committed.
`scripts/loop_tweak_replication.py` takes every cycle that started from the promotion to 2026-10-25 14:27. It joins each
to its run by val_f1, for the run's ROC AUC and AP prevalence lift. Of the 580 cycles, 34 ran for 60 minutes (the nights
up to 10-20) and are left out. The other 546 ran 15 minutes, and all are matched. Every row is in
`reports/loop_tweak_replication_2026-10-25.json`.

**Method.** The window holds eight code epochs: the promotion's checkout, then each of seven merges into it that
touched what the loop runs (listed in the JSON). A tweak's effect is each of its cycles minus the mean of the other tweaks' cycles that
started under the same code, averaged over its cycles. A t-test on those differences gives each tweak's p, which is
Holm-adjusted across the 26 tweaks, separately for each measure.

**This is exploratory.** I saw `aug_mode_batchgeneratorsv2` stand out before writing the script. A confirmation on
cycles not yet run is registered in `docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md`.

## Result

Each tweak's effect against its epoch's other cycles, with its Holm-adjusted p:

| tweak | cycles | val_f1 | ROC AUC | AP prevalence lift |
|---|---:|---:|---:|---:|
| `aug_mode_batchgeneratorsv2` | 26 | +0.0043 (p 1e-09) | +0.0122 (p 6e-07) | +0.039 (p 2e-04) |
| `use_uamt_False` | 24 | +0.0027 (p 6e-10) | +0.0038 (p 0.3) | +0.006 (p 1) |
| `loss_ink_bce_0.2` | 14 | +0.0017 (p 0.02) | −0.0058 (p 0.02) | −0.017 (p 0.1) |

* **`aug_mode_batchgeneratorsv2` is higher on all three measures.** It is the only tweak whose AUC or AP lift is higher at
  Holm p < 0.05.
  * Its 26 cycles average val_f1 0.2710 (SD 0.0018), against 0.2668 for the rest.
  * Its AUC averages 0.590, against 0.577, and its AP lift 1.218, against 1.179.
  * Its val_f1 and its AUC are both higher in each of the six code epochs it ran in.
  * The tweak swaps the loop's default augmentation, a per-slice Albumentations recipe, for villa's 3D batchgeneratorsv2
    pipeline (`apply_augmentations` in `scripts/training/train.py`). Neither run log holds a warning that it fell back
    to Albumentations.
* **Two other tweaks raise val_f1 alone.** `use_uamt_False` leaves AUC where it was, and `loss_ink_bce_0.2` lowers it.
  val_f1 is the best F1 over a grid of thresholds, so a tweak can move it without ranking ink any better.
* **Its size.** On this sample, predicting ink everywhere scores F1 0.2451 (finding 88), so the incumbent is 0.021
  above it. batchgeneratorsv2 adds 0.004 to that margin, about a fifth.
* **The loop cannot promote it.** The bar is 0.275762: the incumbent plus `F1_NOISE_TOLERANCE`, 0.01.
  * None of the 546 cycles reached it. The highest was 0.2739, a batchgeneratorsv2 cycle.
  * At batchgeneratorsv2's mean and SD, one cycle clears the bar with probability 0.5% (a normal approximation).
  * The bar was set so that an unchanged cycle clears it 0.67% of the time (#109). It equally stops a real gain of
    0.004, about one and a half times the SD of identical cycles (0.0029, #109).

## The step count

On this CPU-bound host, a batchgeneratorsv2 cycle trains fewer steps in its 15 minutes: a median of 980, against 1,290
for the others. As far as these cycles can tell, that is not the cause:
* `batch_size_16` trains a median of 650 steps, and its val_f1 is not higher (−0.0005).
* Across the other tweaks, steps and val_f1 are correlated only through `use_uamt_False`, which trains 4,295 steps. Left
  out, the correlation is −0.03 over 496 cycles.

## What this means for the loop

These are the owner's decisions.
* **A rule over replicates would take it; the single-cycle rule cannot.** The loop already has the replicates: each
  tweak ran 11 to 28 times in these eight days. A rule that compares a tweak's recent cycles with the others' needs
  no new runs.
* **The loop never runs an unchanged cycle.** So the baseline here is the other tweaks, not the incumbent's own config.
  A rule over replicates would want a periodic unchanged cycle as its reference.
* **Promoting batchgeneratorsv2 by hand** is the other route. It would change the recipe every later cycle starts from.

## What it does not say

* **That it reads ink better beyond this sample.** Every cycle is scored on the loop's 400 Fr143 validation patches
  (protocol v3), where AUC is about 0.59.
* **That the gain survives promotion.** Every cycle fine-tunes the same `best_model.pt` for 15 minutes. A
  batchgeneratorsv2 incumbent is a new starting point, and this does not measure it.
* **Which part of the recipe matters.** The two pipelines differ in many ways at once:
  * batchgeneratorsv2 applies 3D spatial transforms to every channel, the ridge channel included;
  * it has its own intensity transforms;
  * four of the scroll augmentations come from villa's own transforms instead of the loop's. Of those four, this
    config turns on only thick-slice simulation.
* **That the baseline is the unchanged config.** Most tweaks sit within 0.001 of each other, so the rest is probably
  near it, but that is not measured.
* **Anything from mean AP.** The run log's `avg_mean_ap` is in the JSON but not used here. It moves with 15 of the 26
  tweaks at Holm p < 0.05, in both directions.
