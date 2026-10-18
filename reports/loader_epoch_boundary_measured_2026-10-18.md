# Persistent loader workers, measured in the loop (2026-10-18)

**Question:** did #113 (persistent loader workers) stop each pass over the training catalogue from costing time
outside the budget, as `loader_epoch_boundary_2026-10-17.md` predicted?

**Answer:** yes. On the first shift with the fix, overhead no longer rises with passes: 0.2 s per boundary (SE 0.6),
against 21.3 s (SE 1.2) before. A 60-minute cycle's overhead fell from a median of 185 s to 97 s, and
`use_uamt_False`, the config the timeout used to kill, completed.

## The data

* **The shift.** The 10-17 night shift, from 21:17:25, when the loop restarted on the merged main (5acb5342, with
  #113), to its end at 07:34: 10 cycles, all 60 minutes, at batch 8 except `batch_size_16`.
* **The command.** `scripts/epoch_boundary_overhead.py --since 2026-10-17T21:17:25` (`epoch_boundary_overhead_persistent.json`).
  `--since` is new: without it, the shift's two cycles from before the restart would mix with the fixed code's. The
  loop rotated run.log at 03:27, so `--run-log` now takes `run.log.old run.log`.
* **The same night's control.** The two cycles before the restart ran the old loader at batch 8: 182 s and 185 s,
  both at 5 boundaries (`control_rows`).

## Before and after

| | before: respawned workers | after: persistent workers |
|---|---:|---:|
| fit | 84 s + 21.3 s per boundary (SE 1.2) | 98 s + 0.2 s per boundary (SE 0.6) |
| cycles, residual SD | 72, 16 s | 10, 7 s |
| 60-minute cycles at 5 boundaries | median 185 s (11 cycles, 177–199) | median 97 s (9 cycles, 91–114) |

The "before" column is `epoch_boundary_overhead_workers.json`: the 10-16/17 shifts, the 72 cycles the first
report's table uses. SE is the slope's standard error.

* **The killed config.** `use_uamt_False` made 17,020 steps at batch 8, 18 passes. The old fit predicts 468 s of
  overhead, past the timeout's 300 s margin. It took 101 s and scored val_f1 0.2584, the lowest of the shift's ten
  cycles. That is one trial.

## What it does not say

* **The saving is 88 s per 60-minute cycle, not the 106 s predicted** (5 boundaries × 21.3 s). The restart also
  pulled #112 and #115–#117. #116 changes the UA-MT unlabeled grid. This shift does not separate their costs from
  the loader's.
* **The gain in cycles is small.** A 60-minute cycle takes 3,697 s instead of 3,785 s, which is 2.4% more cycles per
  shift. What changed is that a config's speed no longer decides whether it finishes. Before, the fit put any
  60-minute cycle of 11 or more passes past the margin.
* **The 15-minute day cycles are not in it.** They cross about 1 boundary, so the fit predicts about 21 s saved per
  cycle. The day shift was still running when this was measured.
* **What remains is not broken down.** The 97 s a cycle is startup, evaluation and the loop's own work between
  cycles, in shares this does not measure.
