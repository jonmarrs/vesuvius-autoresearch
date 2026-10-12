# villa PR draft: get_ink_metrics.py can run its folds one at a time

**Status: DRAFT, not posted; awaiting the user's go-ahead.** Measured 2026-10-11 (`spiral_out/inkfix_measure/measure.log`;
harness `measure.sh` in the session scratchpad). Patch: `docs/villa_pr_ink_metrics_sequential_folds.patch` (+13/−2),
applies cleanly to `origin/main` `7a7b3f677`. Under the user's
2026-10-11 rule, code-fix PRs may go up to two a week; villa's three-open-PR cap still binds (open: #1928).

## Gate before opening (re-run on the day)

1. The defect is live at current `origin/main`. `get_ink_metrics.py` launches every fold before waiting on any,
   and stacks all fold probabilities before `np.mean`.
2. No existing issue or PR covers it. Searched 2026-10-11 with a positive control (the search finds #1805 and
   #1585): `get_ink_metrics memory`, `OOM`, `folds`.
3. Patch applies to `origin/main`, under 25 lines.
4. Measured on current upstream code, from the measurement log: peak memory and outcome for stock vs
   `--sequential-folds` on an outer strip, and wall time and agreement on an inner one.

## Title

`get_ink_metrics: add --sequential-folds; average folds in place`

## Body

`get_ink_metrics.py` starts all of its fold subprocesses at once, and each holds the whole strip's
probabilities. With one GPU, all three folds run on it at the same time. On a ten-winding outer strip
(w120–w129, 82,660 × 4,260 = 352M px) that does not fit in a 32 GB machine. A fold is killed by the OOM
killer, and the log only shows `FAILED (rc=-9)`.

This PR:
* adds `--sequential-folds`, which waits for each fold before launching the next. It is off by default,
  so nothing changes for multi-GPU runs.
* averages the folds in place instead of stacking them for `np.mean`. The output is bit-identical (checked
  on 2, 3 and 5 float32 folds); peak memory in that step drops from four strip-sized arrays to two.
* prints a hint when a fold dies with rc=-9.

Measured on `origin/main` (7a7b3f677), one RTX 4090, each run in a 26 GiB memory cgroup with swap off:

| strip | mode | result | peak memory | wall time |
|---|---|---|---|---|
| w120–w129, 82,660 × 4,260 | stock | OOM-killed 70 s in, while all three folds ran | ≥ 27.6 GB | – |
| w120–w129 | `--sequential-folds` | ok, `total_fg_pixels` 1,650,752 | 13.8 GB | 1,009 s |
| w010–w019, 26.8M px | stock | ok, 221,561 | 9.1 GB | 127 s |
| w010–w019 | this PR, default | ok, 221,570 | 9.3 GB | 107 s |
| w010–w019 | `--sequential-folds` | ok, 221,564 | 3.6 GB | 185 s |

The pixel counts differ by under 0.005%, which is the scorer's run-to-run GPU nondeterminism (three stock runs on one
fixed strip spread by 0.0032%). Running folds one at a time is slower on a single GPU (prediction 171 s against
92–108 s on the short strip), which is why it is a flag and not the default.

Not changed: the default concurrency, `--procs`, and fold scheduling across several GPUs.
