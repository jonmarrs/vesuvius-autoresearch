# Pre-registration: does `aug_mode_batchgeneratorsv2` beat the loop's other tweaks on cycles not yet run?

**Written 2026-10-25, before any cycle of its window (from 2026-10-25 16:00 PDT) had started.**

## The question

`reports/loop_tweak_replication_2026-10-25.md` (exploratory) found one tweak above the rest on all 26 of the loop's
cycles that ran it since the 10-17 promotion: `aug_mode_batchgeneratorsv2`, villa's 3D batchgeneratorsv2 augmentation
in place of the loop's Albumentations recipe. Against the other tweaks' cycles under the same code, its val_f1 is
+0.0043 higher, its ROC AUC +0.0122 and its AP prevalence lift +0.039. The loop cannot promote it: one cycle must
clear the stored incumbent by 0.01, and no cycle has. I picked that tweak after seeing the data. If the gain recurs on
cycles that did not exist when I picked it, the loop has a replicated improvement its rule cannot take, and the owner
has a reason to promote it or change the rule. If it does not recur, the exploratory result was selection.

## Reachability

The window needs nothing new. The loop runs `aug_mode_batchgeneratorsv2` on its own: 26 of its 546 15-minute cycles
from 10-17 14:02 to 10-25 14:27, about three a day. Its sprint logs and run logs record everything the analysis reads:
`scripts/loop_tweak_replication.py` matched all 546 cycles to their runs in that period.

## The floor

The cycle-to-cycle SD of identical cycles is 0.0029 in val_f1 (0.0019–0.0058, df 7;
`reports/noise_probe_v3_pooled_2026-10-17.md`), measured from the earlier checkpoint. In the exploratory window, the
standing tweak's per-cycle differences from its epoch's other cycles have SD 0.0020 (val_f1), 0.0078 (AUC) and 0.035
(AP lift), n = 26.

## Window

Every 15-minute cycle that starts at or after **2026-10-25 16:00:00 PDT**, in the loop's sprint logs, joined to the run
logs as in the exploratory report. It ends at the first of:
- the end of the 8th `aug_mode_batchgeneratorsv2` cycle (cycles that start after it are dropped);
- 2026-10-29 16:00:00 PDT;
- a promotion (the promoted cycle is the last; later cycles face another incumbent).

The code epochs are the script's `EPOCHS`. If a merge into the loop's checkout changes what it runs during the window,
the epoch list gets that merge before the analysis runs, with the merge's commit and time from the checkout's reflog.
Nothing else in the script may change.

## Predictions, fixed now

Effects are as in the exploratory report: each standing cycle minus the mean of the other tweaks' cycles that started
in its epoch, averaged. Each threshold is about half the exploratory effect, for the regression a picked winner shows.

1. **P1, val_f1 effect ≥ +0.0020.** Exploratory +0.0043; with n = 8 its standard error is about 0.0007. High.
2. **P2, ROC AUC effect ≥ +0.0050.** Exploratory +0.0122, standard error about 0.0027 at n = 8. High.
3. **P3, AP prevalence lift effect ≥ +0.015.** Exploratory +0.039, standard error about 0.012 at n = 8. Moderate.
4. **P4, no standing cycle clears the promotion bar** (incumbent 0.265762 + 0.01). Exploratory: 0 of 26, and a normal
   approximation gives 0.5% per cycle. High.

## Decision rule

| outcome | reading |
|---|---|
| fewer than 6 standing cycles, or fewer than 60 others, by the end of the window | INCOMPLETE: no reading |
| any cycle not matched to its run | UNMATCHED_RUNS: no reading |
| P1 and P2 hold | CONFIRMED: it beats the other tweaks on new cycles, in ranking (AUC) as well as F1 |
| P1 holds, P2 fails | F1_ONLY: the F1 gain recurs, the ranking gain does not; the "ranks ink better" reading is withdrawn |
| P1 fails | NOT_REPLICATED: the exploratory gain was selection; the report's reading is withdrawn |

P3 and P4 are reported, and change no reading. If P4 fails, a standing cycle has promoted itself, which ends the window
at that cycle.

`scripts/loop_tweak_replication.py --registered` implements the window and the table (`REGISTERED`,
`registered_verdict`). `tests/test_loop_tweak_replication.py` checks that a short window gives no reading, that an
unmatched run gives none, that the window is cut at the 8th standing cycle, and each row of the table. The command:

    python3 scripts/loop_tweak_replication.py --registered --since 2026-10-25T16:00:00 --until <end> \
        --sprint-logs 'sprint_logs/sprint_log_2026-10-2*.md' --run-log run.log --out reports/X.json

`<end>` is 2026-10-29T16:00:00, or any earlier time after the 8th standing cycle ends.

## What the result cannot do

- **Show that it reads ink better off this sample.** Every cycle is scored on the loop's 400 Fr143 validation patches
  (protocol v3); AUC is about 0.59 there. A held-out region, or another scroll, is a different measurement.
- **Say the gain survives promotion.** Every cycle fine-tunes the same `best_model.pt`. A promoted batchgeneratorsv2
  checkpoint is a new starting point, and its cycles are not measured here.
- **Name the mechanism.** The two recipes differ in many ways, including the step count: on this CPU-bound host a
  batchgeneratorsv2 cycle trains about 980 steps in 15 minutes, against 1,290 for the others.
- **Compare it with the unchanged config.** The loop never runs a cycle without a tweak, so the baseline is the other
  tweaks.

## Limits

One incumbent, one validation sample, one host, the loop's own tweak schedule (it picks the tweaks, not me).

## Cost

None beyond the loop's own cycles: no GPU time, no pause. The analysis takes about a minute of CPU.
