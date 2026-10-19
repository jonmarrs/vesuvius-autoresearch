# Replication: do 60-minute cycles score higher than 15-minute ones? (2026-10-19)

The replication arm of `cycle_length_gain_prereg_2026-10-18.md`: the 10-18 night shift's 60-minute cycles, compared
with the same 15-minute arm as the first result (`cycle_length_gain_2026-10-18.md`, #133). None of its cycles had run
when the pre-registration was written.

**Answer: no measurable gain again, the pre-registered reading.** The 10-18 night's 12 sixty-minute cycles averaged
val_f1 0.2670 and the 10-18 day's 42 fifteen-minute cycles 0.2656: a difference of +0.0015, Welch 95% interval
−0.0011 to +0.0041. The first arm gave +0.0013 (−0.0014 to +0.0041). In both, the interval spans zero and its top is
under half the 0.01 tolerance, so the extra 45 minutes cannot by themselves buy a promotion.

## The data

* **The command.** `scripts/cycle_length_gain.py --since 2026-10-17T21:17:25 --sprint-logs` (the 10-17 night,
  10-18 day and 10-18 night logs) `--run-log run.log.old run.log`, giving `cycle_length_gain_replication_2026-10-19.json`.
  Naming all three logs gives both pre-registered comparisons in one run. The 10-19 day shift is not an arm.
* **It reproduces the first result.** Its first two arms and their comparisons equal `cycle_length_gain_2026-10-18.json`
  exactly, apart from a field #135 added.
* **#135 changed the script's log parsing after the first result:** it counts a cycle logged `CRASHED (OOM)`, which
  was dropped before, and reads each log once. No cycle in these arms crashed, and #133's version of the scripts
  gives the same output on these logs.
* **Neither stop was reached.** No cycle in any arm was promoted (all 64 were REVERTED), the loop ran 5acb5342
  throughout, and none crashed. Every cycle's step count was matched in run.log.
* **The arm was not entirely unseen when this ran.** At 07:04 I read the night log's cycles 8–11, before running the
  analysis. The analysis was fixed in advance, so this changed nothing in it.

## Results

| | 60-minute (10-17 night) | 15-minute (10-18 day) | 60-minute (10-18 night) |
|---|---:|---:|---:|
| cycles scored | 10 | 42 | 12 |
| mean val_f1 | 0.2669 | 0.2656 | 0.2670 |
| SD | 0.0037 | 0.0027 | 0.0039 |
| highest | 0.2710 | 0.2739 | 0.2718 |
| median steps | 5,100 | 1,275 | 5,260 |

The replication arm's SD is inside the pooled probe's 0.0029 (0.0019–0.0058, #109). Its best cycle, `loss_st_0.2` at
0.2718, came no closer to the promotion bar, 0.2758, than the day's 0.2739.

| comparison with the 15-minute arm | 10-17 night (seen) | 10-18 night (replication) |
|---|---|---|
| all cycles (primary) | +0.0013, −0.0014 to +0.0041: no measurable gain | +0.0015, −0.0011 to +0.0041: no measurable gain |
| without `use_uamt_*` and `batch_size_*` (secondary, descriptive) | +0.0027, +0.0007 to +0.0047: higher | +0.0021, −0.0001 to +0.0042: no measurable gain |

* **The secondary reads differently in the two arms, but its estimates are close.** The replication's interval
  reaches 0.0001 below zero, so `reading()` gives no measurable gain where the first arm gave higher.
* **`use_uamt_False` was the lowest cycle on both nights.** It scored 0.2584 at 60 minutes both times (17,020 and
  17,690 steps), against 0.2706 at 15 minutes (4,380 steps).

**Exploratory, not pre-registered:**
* **Both nights pooled:** 22 cycles, +0.0014 (−0.0004 to +0.0032). Without `use_uamt_*` and `batch_size_*`: +0.0023
  (+0.0008 to +0.0039).
* **Matched tweaks.** All 12 of the night's tweaks also ran by day. Each night cycle minus the day mean of the same
  tweak: +0.0021 over all 12 (95% −0.0013 to +0.0056), and +0.0032 over the 10 without `use_uamt_*` and `batch_size_*`
  (+0.0009 to +0.0055), the night higher in 8 of those 10. The first arm gave +0.0032 over its 8 (+0.0010 to +0.0053).

**Reading:** over all cycles, 45 more minutes bought no measurable gain in either arm. For a tweak that leaves the
step count alone they may buy about +0.002 to +0.003, a fifth to a third of the tolerance. The highest interval top
in this report is 0.0056, about half of it.

## Side load during the replication arm

| when (PDT) | what | overlapping cycle (steps) |
|---|---|---|
| 10-18 22:16–22:55 | writing #133's report and tests, pre-commit, two merges, tests in a new worktree, a worktree disk-use inventory | `weight_decay_0.1` (4,590) |
| 10-19 04:25–04:30 | git and gh queries of seconds each | `loss_ink_dice_0.6` (5,100) |
| 10-19 07:02–07:10 | a git push to villa, file reads, gh queries, a 0.23 s test | `loss_fiber_bce_0.1` (5,130) |

* **The first row was not light, and it is the arm's lowest step count.** Its 10 cycles without step-changing
  configs trained 4,590–5,430 steps, median 5,260; the 10-17 night's 8 trained 4,660–5,270.
* **Leaving `weight_decay_0.1` out does not change the reading:** +0.0017 (−0.0011 to +0.0044), no measurable gain.

## What it does not say

* **Both 60-minute arms are compared with one 15-minute arm.** They replicate each other, not the day arm.
* **The arms try different tweaks**, and day and night differ in more than the budget, as the pre-registration
  says.
* **It is about the loop's val_f1,** on its fixed validation sample, not about reading ink.
* **What to do with the night's hours is the owner's call.** The night's cycles started 61.5 minutes apart and the
  day's 16.5, so a 15-minute night would try about 3.7 times as many candidates: about 44 in the hours that held
  these 12. More candidates also means more chances of a no-change promotion. At #109's point rate of 0.67% per
  no-change cycle, a night of 12 cycles has a 7.7% chance of at least one, and a night of 44 a 25.6% chance. That rate was measured on 15-minute cycles, and its
  interval runs from 0.009% to 11.2%.
