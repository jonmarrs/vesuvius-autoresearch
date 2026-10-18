# Pre-registration: do 60-minute cycles score higher than 15-minute ones? (2026-10-18)

Written on 2026-10-18 at about 08:50 PDT, after the 10-18 day shift's first three cycles and before any later one
was read.

**Question.** Every cycle fine-tunes `best_model.pt` for its budget, 15 minutes by day and 60 by night. On the same
code and incumbent, does a 60-minute cycle score a higher val_f1 than a 15-minute one?

**Why it matters.** A night shift spends four times a day cycle's training on each candidate. #112 found that tweaks
after the first promotion under 0.01 spread like identical cycles, but all 17 of them ran 15 minutes. If 60 minutes
buys nothing measurable, the night shift's extra hours buy no measurable val_f1. What to do with them is the owner's
call.

## Data

* **Source:** the sprint logs, read by `scripts/cycle_length_gain.py` with `--since 2026-10-17T21:17:25`. That is
  when the loop restarted on 5acb5342, the code it still runs, with incumbent `batch_size_8` (0.265762).
* **60-minute arm:** the 10-17 night shift's 10 cycles after that restart. **I had seen them before writing this.**
* **15-minute arm:** every cycle of the 10-18 day shift. I had seen cycles 1–3 (`loss_ink_bce_0.4`,
  `aug_mode_batchgeneratorsv2`, `ema_decay_0.9999`).
* **Replication arm:** the 10-18 night shift's 60-minute cycles, compared with the same 15-minute arm. None had run
  when this was written.
* **Stops:**
  * at the first promotion (SUCCESS), which is kept; later cycles start from another checkpoint.
  * at a restart onto other code (a pull into the main checkout). The analysis is then run with the sprint logs up to
    that restart.
* **Crashed cycles** have no val_f1. They are counted, not scored.

## Measures

* **Primary:** for each 60-minute arm, its mean val_f1 minus the 15-minute arm's mean, with a Welch 95% interval.
* **Reading, fixed now** (`reading()` in the script; 0.01 is train.py's `F1_NOISE_TOLERANCE`):
  * the interval above 0: **higher**, by the interval;
  * the interval below 0: **lower**;
  * the interval spans 0 and stays below 0.01: **no measurable gain**. The extra 45 minutes cannot by itself buy a
    promotion;
  * the interval spans 0 and reaches 0.01: **inconclusive**.
* **Secondary, descriptive:**
  * the same comparison without `use_uamt_*` and `batch_size_*` tweaks, which change how many steps a budget buys;
  * each arm's SD against the pooled probe's 0.0029 (0.0019–0.0058, #109);
  * each arm's median steps, from run.log, to show how much training each budget bought.

## Limits, stated now

* **The first 60-minute arm was seen.** This fixes the analysis, not the arm. The replication arm is unseen.
* **The arms try different tweaks.** Both are draws from the loop's tweak distribution, whose effects #112 found
  inside the noise. Arms with very different tweak mixes are a confound this does not remove.
* **Day and night differ in more than the budget.** CPU side jobs by day cut the loop's throughput, so a 15-minute
  cycle may train less than its budget suggests. The median steps per arm show it. I will run no long side job
  during the 15-minute arm.
