# Do 60-minute cycles score higher than 15-minute ones? (2026-10-18)

Pre-registered in `cycle_length_gain_prereg_2026-10-18.md` (commit a53531ff, 08:45 PDT), when the day shift's first
three cycles had been read and no later one.

**Answer: no measurable gain, the pre-registered reading.** On the same code and incumbent, the 10-17 night's 10
sixty-minute cycles averaged val_f1 0.2669 and the 10-18 day's 42 fifteen-minute cycles 0.2656: a difference of
+0.0013, Welch 95% interval −0.0014 to +0.0041. The interval spans zero and its top is under half the 0.01 tolerance,
so the extra 45 minutes cannot by themselves buy a promotion. The replication arm, the 10-18 night, is still running.

**Replicated 2026-10-19** (`cycle_length_gain_replication_2026-10-19.md`): the 10-18 night's 12 cycles read no measurable
gain too.

## The data

* **The command.** `scripts/cycle_length_gain.py --since 2026-10-17T21:17:25 --sprint-logs` (the 10-17 night and
  10-18 day logs) `--run-log run.log.old run.log`, giving `cycle_length_gain_2026-10-18.json`.
* **One change from the pre-registered command.** Its glob would also have read the 10-18 night shift, the
  replication arm, which was on its third cycle when this ran. I named the two logs instead, so the partial
  replication arm was never computed. `--sprint-logs` now takes a list of paths; a test pins that naming the logs
  gives the same arms as a glob over them.
* **Neither stop was reached.** No cycle in either arm was promoted (all 52 were REVERTED), the loop ran 5acb5342
  throughout, and none crashed. Every cycle's step count was matched in run.log.

## Results

| | 60-minute (10-17 night) | 15-minute (10-18 day) |
|---|---:|---:|
| cycles scored | 10 | 42 |
| mean val_f1 | 0.2669 | 0.2656 |
| SD | 0.0037 | 0.0027 |
| highest | 0.2710 | 0.2739 |
| median steps | 5,100 | 1,275 |

Both SDs are inside the pooled probe's 0.0029 (0.0019–0.0058, #109). The closest any cycle came to the promotion bar, 0.2758
(the incumbent's 0.2658 plus 0.01), was the day's 0.2739.

| comparison | difference | 95% interval | reading |
|---|---:|---:|---|
| all cycles (primary) | +0.0013 | −0.0014 to +0.0041 | no measurable gain |
| without `use_uamt_*` and `batch_size_*` (secondary, descriptive) | +0.0027 | +0.0007 to +0.0047 | higher |

* **The secondary differs from the primary mostly through one config.** `use_uamt_False` scored 0.2584 at 60 minutes
  (17,020 steps, the night's lowest) and 0.2706 at 15 minutes (4,380 steps). Leaving it out raises the night's mean
  and lowers the day's.
* **Matched tweaks (exploratory, not pre-registered).** All 10 of the night's tweaks also ran by day, once or twice.
  Each night cycle minus the day mean of the same tweak: +0.0013 over all 10 (95% −0.0025 to +0.0052), and +0.0032
  over the 8 without `use_uamt_*` and `batch_size_*` (+0.0010 to +0.0053), the night higher in 7 of those 8.

**Reading:** 45 more minutes may buy about +0.003 val_f1 for a tweak that leaves the step count alone. That is about
a third of the tolerance, and no interval above reaches past 0.0053, about half of it.

## Side load during the 15-minute arm

I ran no long side job, but I did run short ones at nice 19. The cycles that overlapped them trained:

| when (PDT) | what | overlapping cycles (steps) |
|---|---|---|
| 09:33–09:40 | a 120 s `find`, then seconds-long tests | `multi_task_heads_False` (1,280) |
| 15:40–15:55 | a scratch Python 3.14 environment and four short test runs | `batch_size_16` (650, as at 11:10), `lr_0.001` (1,290) |
| 17:05–17:20 | pip dry runs, a worktree checkout, pre-commit and 20 s of tests | `multi_task_heads_False` (1,220), `target_fiber_source_sobel_z` (1,120) |

The day's 36 cycles without step-changing configs (`use_uamt_*`, `batch_size_*`, and `aug_mode_*`, which trained about
1,000) trained 1,120–1,320 steps, median 1,280. The 17:13 cycle's 1,120 is the arm's lowest, and it overlapped the checkout. The day arm's median,
1,275 steps, is the night's 5,100 divided by four, so the day cycles got their budget's training.

## What it does not say

* **The 60-minute arm was seen before the pre-registration.** The replication arm, the 10-18 night, has not been
  read. It is compared with this same 15-minute arm when that shift ends, about 07:35 on 10-19, unless a promotion or
  a restart onto other code stops it first.
* **Day and night differ in more than the budget.** The step counts above show the day arm trained its full budget;
  they do not rule out every difference between the two shifts.
* **It is about the loop's val_f1,** the number the loop promotes on, on its fixed validation sample, not about
  reading ink.
* **What to do with the night's hours is the owner's call.** On average the day's cycles started 16.5 minutes
  apart and the night's 61.7, so a 15-minute shift tries 3.7 candidates in the time a 60-minute shift tries one.
