# Within a tweak, the loop's cycles that train fewer steps rank ink better and score the same F1 (2026-10-26)

**Exploratory, on the 546 cycles before the batchgeneratorsv2 window**, from the committed record
`reports/loop_tweak_replication_2026-10-25.json` (last cycle start 2026-10-25 14:10:57; the window opened at 16:00).
Written before the window's readout. No measure of a window cycle was read. Script `scripts/loop_steps_vs_ranking.py`,
record `reports/loop_steps_vs_ranking_2026-10-26.json`.

**Question.** The [confirmation's registration](../docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md) cannot
name the mechanism of `aug_mode_batchgeneratorsv2`'s gain, and names step count as one difference: its cycles train
about 960 steps in 15 minutes, the others about 1,260. Every cycle fine-tunes the same incumbent for the same wall time.
If training fewer steps moves the measures by itself, part of the gain is "trained less", which needs no new
augmentation.

**Method.** Within one tweak and one code epoch the recipe is fixed, and a cycle's steps differ from its group's mean
by the host's load alone (SD 86 steps; half lie within 35 of their group's mean). Each measure's deviation from its group's mean
is regressed on the steps' deviation through the origin: fixed effects for tweak × epoch. 454 cycles in 95 groups of
two or more; batchgeneratorsv2's own cycles are left out. Checks: the steps shuffled within each group (10,000 times),
whole days resampled (only 8 days, so a rough check), time within the group as a second regressor, each tweak left
out in turn, the sign of each tweak's own slope (25 tweaks with 8 or more cycles), and the deviations in bins.

## Result

Per 100 more steps, within a tweak:

| measure | slope | 95% CI | permutation p | days resampled | with time | one tweak left out | tweaks with a negative slope |
|---|---:|---:|---:|---:|---:|---:|---:|
| val_f1 | −0.00005 | −0.00024 to +0.00014 | 0.546 | −0.00016 to +0.00017 | −0.00005 | −0.00014 to +0.00001 | 12 of 25 |
| ROC AUC | −0.00085 | −0.00153 to −0.00018 | 0.024 | −0.00134 to +0.00008 | −0.00074 | −0.00124 to −0.00067 | 16 of 25 |
| AP prevalence lift | −0.0045 | −0.0078 to −0.0011 | 0.013 | −0.0066 to −0.0007 | −0.0038 | −0.0066 to −0.0038 | 18 of 25 |

The same deviations in bins, each cycle against its own group's mean:

| steps from the group's mean | cycles | mean steps | val_f1 | ROC AUC | AP prevalence lift |
|---|---:|---:|---:|---:|---:|
| 150 or more fewer | 24 | −269 | +0.0003 | +0.0031 | +0.017 |
| 50 to 150 fewer | 42 | −82 | +0.0003 | +0.0004 | +0.001 |
| within 50 | 320 | +11 | −0.0001 | 0.0000 | 0.000 |
| 50 to 150 more | 62 | +83 | +0.0001 | −0.0008 | −0.004 |
| 150 or more more | 6 | +216 | −0.0004 | −0.0052 | −0.021 |

**Reading.** At a fixed recipe, a cycle that trains fewer steps ranks the validation patches better (ROC AUC, AP
prevalence lift) and scores the same val_f1. The AP-lift slope holds under every check. The AUC slope holds with a
tweak left out and with time added; the day resampling's interval just reaches zero with 8 days, and 16 of 25 tweaks
slope its way. Confidence: moderate for AUC, moderate to high for AP lift. No check finds a val_f1 slope. Cycles that lost about 270 steps to load gained +0.0031 AUC,
which measures batchgeneratorsv2's step deficit directly, without extrapolating the line.

## What it means for batchgeneratorsv2

Its cycles trained 305 fewer steps than the epoch's other cycles of the same step cost (418 fewer counting UAMT off and
batch 16, whose steps are of another size). The slopes above, times that gap, against its measured effects:

| measure | its effect | from its 305 fewer steps (95% CI) | share | beyond its steps |
|---|---:|---:|---:|---:|
| val_f1 | +0.0043 | +0.0001 (−0.0004 to +0.0007) | 3% (−10% to 17%) | +0.0041 |
| ROC AUC | +0.0122 | +0.0026 (+0.0006 to +0.0047) | 21% (5% to 38%) | +0.0096 |
| AP prevalence lift | +0.039 | +0.014 (+0.003 to +0.024) | 35% (9% to 61%) | +0.025 |

None of its F1 gain is fewer steps. About a fifth of its AUC gain and a third of its AP-lift gain are the size that
losing the same steps to load gives other tweaks. What is left clears the confirmation's own thresholds (P2 AUC
≥ +0.005, P3 AP lift ≥ +0.015) on this record.

This rests on one assumption: batchgeneratorsv2's missing steps act like load's. For it: batchgeneratorsv2 keeps the
model, loss, batch size and learning rate, and loses steps because its augmentation starves the CPU-bound loader, as
load does. The slope does not carry across recipes that change what a step is. UAMT off trains about 2,900 more
steps than the rest and scores +0.0038 AUC; batch 16 trains about 630 fewer and scores −0.0015. batchgeneratorsv2's own
26 cycles slope the same way and more steeply (−0.0075 AUC per 100 steps), on too few cycles to read.

## For the window's readout (reported; changes no reading)

The registered predictions and reading stay as registered. At the readout, `window_adjustment` reports, on the
confirmation's own output cut at the 8th standing cycle: the standing tweak's step gap in the window, and each effect
next to the slope above times that gap. The slopes are fixed here, before the window's measures are read.

My full test suites ran beside the loop during the window (their times are recorded for the readout). They took CPU from
whichever cycles they overlapped, so by this result those cycles' AUC and AP lift would read a little high. The readout
will list the overlapping cycles by tweak.

## What this cannot do

- **Prove the cause.** Load is not assigned. It is causal only if a busy host changes nothing in a cycle but its step
  count. The data loader yields the same kind of batches either way, and the learning rate follows the elapsed share
  of the time budget, not the step count (`budget_lr_factor` in `train.py`): a slowed cycle runs the same schedule
  with fewer updates.
- **Say where the incumbent stands.** Its own ROC AUC on these 400 patches is not in any log I can read. Whether every
  cycle's fine-tune ranks worse than the incumbent it starts from would take one evaluation of `best_model.pt`.
- **Reach beyond this record.** One incumbent, 8 days, the 15-minute cycle.

**Also seen.** More steps buy no F1 either, which fits the finding that a 60-minute cycle gains nothing on a 15-minute one
(`reports/cycle_length_gain_prereg_2026-10-18.md`).

**Cost.** Ten seconds of CPU.

**October 27 follow-up:** the incumbent's saved checkpoint already contains
ROC AUC 0.574202 and AP prevalence lift 1.169277, with a complete 400-patch
validation record. [The saved-reference comparison](loop_incumbent_reference_2026-10-27.md)
extracts those values without inference and compares only the published
pre-window cycles. It narrows the open question above; it is not a fresh
evaluation or an unchanged-training control and changes no registered reading.
