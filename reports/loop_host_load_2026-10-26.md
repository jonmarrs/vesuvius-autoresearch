# The host's measured load accounts for most of a loop cycle's step spread within a tweak, and gives the same steps-to-ranking slope (2026-10-26)

**Exploratory, on the cycles before the batchgeneratorsv2 window**, from the committed record
`reports/loop_tweak_replication_2026-10-25.json` and the host's sysstat CPU samples for 10-18 to 10-25. Written before
the window's readout. No measure of a window cycle was read, and no sysstat sample from the window was read. Script
`scripts/loop_host_load.py`, each cycle's load in `reports/loop_host_load_cycles_2026-10-26.json`, record
`reports/loop_host_load_2026-10-26.json`.

**Question.** [#250](loop_steps_vs_ranking_2026-10-26.md) finds that within one tweak, a cycle that trains fewer steps
ranks ink better (ROC AUC, AP prevalence lift) and scores the same val_f1. It assumes two things it could not measure:
that a cycle's steps differ from its group's mean by the host's load alone, and that load changes nothing in a cycle
but its steps. The host's own CPU record measures that load, independently of the loop's logs.

**Method.** sysstat samples the host's CPU every 10 minutes. A cycle's load is the time-weighted mean, over its 990 s
(the median gap between cycle starts: 900 s of training and its setup), of busy (100 − %idle, in points of the host's
4 CPUs together) and of %nice (processes above nice 0, where side jobs run; the loop runs at nice 0). Of the 546
cycles, 521 have a load: the 18 on 10-17 come before the oldest sysstat file the host keeps, and 7 span 23:50 to
00:00, which sysstat's daily files leave unsampled. Within tweak × epoch, with batchgeneratorsv2's own cycles left out
as in #250: 448 cycles in 95 groups over 8 days (SD of the steps 86, of busy 10.9 points). Busy is the instrument for
the steps. The checks: the instrumented slope with whole groups and with whole days resampled (2,000 times), the
slope on the part of the steps that load leaves, and busy beside the steps.

## Result

**Load explains most of the steps' spread.** Within a group, each point of busy costs 6.1 steps (SE 0.27; F 536), and
busy alone explains 60% of the steps' spread around their group means. Fit with %nice beside it, a point of load at
nice 0 costs 9.6 steps and a point at nice 19 about 4.9 (−9.6 + 4.7).

**Load's part of the steps gives the same slope as the rest.** Per 100 more steps, within a tweak:

| measure | all steps (#250's fit, on these cycles) | load's part (instrumented) | groups resampled | days resampled | the part load leaves |
|---|---:|---:|---:|---:|---:|
| val_f1 | −0.00005 | −0.00012 | −0.00041 to +0.00019 | −0.00043 to +0.00040 | +0.00005 |
| ROC AUC | −0.00083 | −0.00081 | −0.00166 to +0.00005 | −0.00138 to +0.00044 | −0.00087 |
| AP prevalence lift | −0.0043 | −0.0042 | −0.0082 to −0.0003 | −0.0067 to +0.0014 | −0.0044 |

**Given the steps, load moves no measure that can be seen, but the check is weak.** Per standard deviation of busy,
fit beside the steps, against what that much load does through the steps it costs:

| measure | load beside the steps (95% CI) | load through its steps |
|---|---:|---:|
| val_f1 | +0.00011 (−0.00014 to +0.00036) | +0.00003 |
| ROC AUC | −0.00004 (−0.00096 to +0.00088) | +0.00056 |
| AP prevalence lift | −0.0001 (−0.0047 to +0.0044) | +0.0029 |

**Reading.** #250's first premise holds. Load measured outside the loop accounts for 60% of the within-tweak spread
in the steps, and the instrument is strong. Load's part of the steps and the part it leaves give the same AUC and AP
lift slopes as all the steps together (AUC −0.00081 and −0.00087 against −0.00083; #250's 454 cycles gave −0.00085), so the slope is not carried by
some other source of step variation. By themselves the instrumented slopes are imprecise: AUC's interval just reaches
zero with groups resampled, and AP lift's excludes zero with groups resampled but not with days. The second premise,
that load acts only through the steps, has a point estimate of no effect beside the steps, but its interval is wider
than the step channel itself. It cannot rule out a direct effect of load as large as the one through the steps.
Confidence: high that load drives the steps' spread; moderate that the slope is load's; the direct effect is untested
at a useful power.

## A correction to #250: where batchgeneratorsv2 loses its steps

#250 said batchgeneratorsv2 "loses steps because its augmentation starves the CPU-bound loader, as load does". The
augmentation does not run in the loader. `apply_augmentations` (`scripts/training/train.py`) runs inside each
training step, sample by sample, on the batch after it has moved to the GPU. Its cycles run the host no busier than
the epoch's other cycles: −3.0 points (SE 2.6). UAMT off, which trains about 2,900 more steps, runs it +16.7 points
busier (SE 2.7). So batchgeneratorsv2's steps go to serial work inside each step, not to a starved loader. This PR
corrects the sentence in #250's script and report.

What #250's window adjustment assumes is unchanged: a cycle that trains fewer steps with the same model, loss, batch
size and time-based learning-rate schedule loses what load's lost steps lose. Both kinds of cycle make fewer updates
on the same schedule. That this is all batchgeneratorsv2's missing steps cost is still an assumption, and this
measures load, not it.

## For the window's readout (reported; changes no reading)

The registered predictions and reading stay as registered. sysstat deletes a file once it is more than 7 whole
days old (`HISTORY=7`, `find -mtime +7`). The window's files (`sa25` to `sa29`) must be copied to `local_data/sysstat`
before that; `sa25` goes early on 11-03. At the readout, `cycles` makes the window's load table from the confirmation's output,
and `window` reports, cut at the 8th standing cycle: the standing tweak's busy and %nice beside the other tweaks', and
by tweak, the cycles a side job overlapped (mean %nice of 10 or more: a nice job on 40% or more of one CPU). That list
covers every job run above nice 0, whoever ran it, which my side-job ledger cannot. A job at nice 0 (the loop's own
priority) shows only in busy, and the standing tweak's busy beside the others' is reported for that.

## What this cannot do

- **Assign load.** Busy is measured, not set. Anything that loads the host and also changes training passes through
  it. A GPU job of another session's, for one, shows in no CPU figure.
- **Separate the loop from the rest.** Busy includes the loop's own work. Within a group the recipe is the same, but a
  slowed cycle also does less work, which biases the first stage toward zero, not away from it.
- **Resolve a cycle finely.** One sample per 10 minutes, about 1.7 per cycle.

**Cost.** One second of CPU.
