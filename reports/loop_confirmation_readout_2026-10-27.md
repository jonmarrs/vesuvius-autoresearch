# The batchgeneratorsv2 confirmation: the registered command gives no reading; with each run pinned by its log header, all four predictions hold (2026-10-27)

**Readout of [the registered confirmation](../docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md) and of
[the replicate rule's window test](../docs/preregistration/2026-10-26_loop_replicate_rule_window.md).** The window ran
from 2026-10-25 16:00 PDT to the end of the 8th `aug_mode_batchgeneratorsv2` cycle, 2026-10-27 05:19:55: 135 cycles in
one code epoch (`139c6873`; the loop's checkout did not change after 10-25 00:09:45), with no promotion. The registered
command (Amendment 1's, `--until 2026-10-27T05:19:55`) ran at about 08:12 on the live logs. It ran again at 08:14 on a
copy of its inputs (`local_data/loop_logs/readout_2026-10-27`, with `SHA256SUMS`) and gave the same bytes:
`reports/loop_tweak_confirmation_2026-10-27.json`.

## The registered result: no reading

| test | status | reading |
|---|---|---|
| confirmation (`loop_tweak_replication.py --registered`) | UNMATCHED_RUNS | none |
| replicate rule (`loop_replicate_rule.py --window`) | UNMATCHED_RUNS | none |

The registered join left 7 of the 135 cycles unmatched, and the decision rule gives no reading when any cycle is not
matched to its run. The replicate rule's registration gives none when the confirmation gives none. As registered,
the window answers nothing.

## Why: a fault in the join, not a missing run

The join gives a cycle the runs with its val_f1 (six decimals) that faced its incumbent, and leaves it unmatched when
there are more or fewer of them than window cycles with that value. Amendment 1 added `run.log.old` so that a rotation
could not lose the window's first runs. That file also holds the runs before the window, which faced the same
incumbent and which no window cycle claims. Each of the 7 cycles has a val_f1 that one of those earlier runs also
scored: two runs, one claim, so unmatched. The loop heads every run with `--- DAY|NIGHT SHIFT CYCLE N: <tweak> ---`, and
the sprint log numbers its cycles the same way. For every one of the 7, one run carries the cycle's own shift, number
and tweak, and the other is an earlier cycle of another tweak:

| cycle start | tweak | its run (`run.log`) | the earlier run with its val_f1 (`run.log.old`) |
|---|---|---|---|
| 10-25 21:23:27 | ridge_sigma_2.0 | NIGHT 9, ridge_sigma_2.0 | DAY 13, loss_ink_bce_0.4 |
| 10-26 06:40:25 | loss_ink_bce_0.2 | NIGHT 43, loss_ink_bce_0.2 | DAY 14, weight_decay_0.1 |
| 10-26 09:25:59 | loss_fiber_bce_0.1 | DAY 9, loss_fiber_bce_0.1 | NIGHT 3, loss_ink_bce_0.2 |
| 10-26 12:45:24 | ridge_sigma_3.0 | DAY 21, ridge_sigma_3.0 | DAY 18, multi_task_heads_False |
| 10-26 16:54:25 | target_fiber_source_sobel_z | DAY 36, target_fiber_source_sobel_z | DAY 8, lr_1e-05 |
| 10-27 00:23:52 | ridge_sigma_3.0 | NIGHT 20, ridge_sigma_3.0 | DAY 39, lr_0.001 |
| 10-27 03:41:38 | lr_0.001 | NIGHT 32, lr_0.001 | DAY 7, consistency_weight_0.05 |

None of the 7 is batchgeneratorsv2. Their val_f1 comes from the sprint log and was in every effect; only their AUC,
AP lift and steps were missing. The exploratory record did not hit this because its cycles claimed those earlier runs.

## The audit

`scripts/loop_confirmation_audit.py` pins a run to a cycle when val_f1, incumbent, shift, cycle number and tweak all
agree. All 128 of the registered join's matches pass that check. Each of the 7 unmatched cycles has exactly one run
that passes, and the audit gives it that run (`reports/loop_confirmation_audit_2026-10-27.json`). It then recomputes
the registered verdict with the registered functions on those rows (`reports/loop_tweak_confirmation_corrected_2026-10-27.json`).

## The reading with the audited join (post hoc, not the registered reading)

| prediction | threshold | exploratory (n = 26) | window (n = 8) | holds |
|---|---:|---:|---:|---|
| P1 val_f1 effect | ≥ +0.0020 | +0.0043 | +0.00435 (t 8.98) | yes |
| P2 ROC AUC effect | ≥ +0.0050 | +0.0122 | +0.0110 (t 4.66) | yes |
| P3 AP prevalence lift effect | ≥ +0.015 | +0.039 | +0.0419 (t 3.06) | yes |
| P4 no standing cycle clears 0.275762 | | 0 of 26 | 0 of 8 (best 0.27425) | yes |

**CONFIRMED.** On cycles that did not exist when it was picked, batchgeneratorsv2 again beats the loop's other tweaks
by about the exploratory margin, in val_f1 and in ranking. Its 8 cycles average val_f1 0.27151 against 0.26717 for the
127 others, and ROC AUC 0.5896 against 0.5786. It is the only tweak above +0.0026 in val_f1 or +0.0059 in AUC.

**The replicate rule: TAKES_CONFIRMED_GAIN.** The rule frozen before the window (val_f1 and AUC, t > 4.5, at least 6
cycles) first promotes batchgeneratorsv2, at its 6th window cycle (10-26 18:33:16, score 7.17: t 7.81 on val_f1, 7.17
on AUC), the earliest it can. Its score was 4.05 at the 7th cycle and 4.66 at the 8th. Q1 holds; Q2 (that the rule
would not take it within the window) fails, which the power table gave a 41% chance at the full effect. On the window's
own cycles with the labels shuffled, the rule promotes in 1 of 1,000 shuffles (0 of 1,000 centred). The candidate it
would promote is kept: `local_data/loop_candidates/window_2026-10-25/candidate_20261026-184935.pt` (sha256
`c80885969cc5b3d4…`). Its saved metadata is that cycle's: val_f1 0.271004, ROC AUC 0.5884, AP lift 1.2379,
`aug_mode` batchgeneratorsv2, complete v3 validation.

## Robustness

| rows | P1 val_f1 | P2 AUC | P3 AP lift | reading | replicate rule |
|---|---:|---:|---:|---|---|
| audited join (above) | +0.00435 | +0.0110 | +0.0419 | CONFIRMED | 6th cycle, score 7.17 |
| the 7 dropped instead (120 others) | +0.00433 | +0.0111 | +0.0431 | CONFIRMED | 6th cycle, score 7.28 |
| cycles a side job overlapped dropped (114 cycles, 7 standing) | +0.00432 | +0.0108 | +0.0407 | | |

The reading does not depend on how the 7 are handled. The host's sysstat record covers 133 of the 135 cycles (2 span
the 23:50–00:10 gap it leaves each day; `reports/loop_host_load_window_2026-10-27.json`). batchgeneratorsv2's cycles
ran the host no busier than the others: −1.4 points of busy (SE 4.0), −0.8 of %nice (SE 3.1). A job above nice 0 (mean
%nice of 10 or more) overlapped 1 of its 8 cycles (10-26 05:01, my 05:09–05:30 job) and 18 of the other 125.

**Its fewer steps** (#250's slopes, fixed before the window; reported, changes no reading). batchgeneratorsv2 trained
308 fewer steps than its epoch's other cycles of the same step cost (UAMT off and batch 16 left out, as in #250), as
before the window (305); its median is 990 against 1,310 for all the others. At #250's
within-tweak slopes that gap accounts for +0.0026 of its +0.0110 AUC effect (24%), +0.014 of its +0.042 AP lift (33%)
and +0.0001 of its val_f1 effect (3%). What is left, +0.0084 AUC and +0.028 AP lift, still clears P2's and P3's
thresholds. That the fewer steps cost what load's fewer steps cost is an assumption ([#252](loop_host_load_2026-10-26.md)).

Confidence: high that batchgeneratorsv2 scores higher than the loop's other tweaks on this validation sample, in
val_f1 and in ranking (n = 8, t 9.0 and 4.7, the exploratory size, unchanged by how the 7 are handled or by side
jobs). Moderate that the AUC gain is mostly beyond its fewer steps. The reading itself is post hoc; see below.

## What I saw, and when

Of the window, before the readout I had read only cycle names and times (to count the standing tweak's cycles). The
registered command printed its effects table for every tweak with its verdict: batchgeneratorsv2 +0.0043 val_f1,
+0.0111 AUC, +0.0431 AP lift, computed without the 7 cycles' AUC and AP lift. I diagnosed the join after that, so the
audit was written with those numbers seen. It does not choose among runs by score: a run is the cycle's only when the
loop's own header and number name the cycle. Dropping the 7 instead gives the same reading.

My side jobs during the window, all at nice 19 (PDT): 10-25 15:33–16:01, 19:11–19:36, 19:36–20:02; 10-26 04:10–04:32,
04:33–04:54, 05:09–05:30, 05:58–06:19, 08:28–08:49, 10:39–11:07, 12:39–13:17, 19:17:46–19:44:41. None from 10-27 before
the cut. Jobs of other sessions above nice 0 are in the sysstat listing above; a job at nice 0 shows only in busy.

## Faults in the registered scripts (unchanged here)

The registrations froze these scripts, so this PR changes none of them.
- **Runs outside the window count in the join.** Runs before it (above) and runs after it both do. A later cycle that
  repeats a window cycle's val_f1 would turn a re-run of the registered command into UNMATCHED_RUNS. The copied inputs
  fix this readout's bytes.
- **The cut skips exactly 8.** `registered_verdict`, `loop_replicate_rule.window_test` and
  `loop_steps_vs_ranking.window_adjustment` cut only when there are more than 8 standing cycles. With exactly 8 and an
  `--until` past the 8th's end, cycles after it would be counted. Here `--until` is the 8th's end, the next cycle
  starts at that second and is excluded, and the last row is the 8th standing cycle. (#252's review fixed the same
  in `loop_host_load.window`.)

## The owner's decisions (2026-10-27)

- **The audited reading is accepted**, as post hoc; the registered result on record remains UNMATCHED_RUNS (Amendment
  2 of the [confirmation's registration](../docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md)).
- **batchgeneratorsv2 is to be promoted** with the replicate rule's candidate, the 6th window cycle's (kept above;
  PR #256 prepares it).
- **The replicate rule is to be adopted** in the live loop, beside the 0.01 margin.

## What this cannot do

- **Show that it reads ink better off this sample.** Every cycle is scored on the loop's 400 Fr143 validation patches
  (protocol v3).
- **Say the gain survives promotion.** Every cycle fine-tuned the same `best_model.pt`.
- **Name the mechanism.** The recipes differ in more than the step count.
- **Compare it with the unchanged config.** The baseline is the other tweaks.

**Cost.** Seconds of CPU, beside the loop.
