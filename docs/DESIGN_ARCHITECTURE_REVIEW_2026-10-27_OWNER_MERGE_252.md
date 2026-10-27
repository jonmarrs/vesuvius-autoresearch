# Design and architecture review — the owner's #252 (the host's load and the steps)

Date: 2026-10-27. Baseline: `511d85fc` (main after the owner's #252).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 14:16–16:16 UTC firings. The 07:16–13:15 firings found main unmoved after #253.

#252 measures each pre-window cycle's host load from sysstat's CPU samples. It asks whether that load drives the
within-tweak step spread that #250 reads (`scripts/loop_host_load.py`, `reports/loop_host_load_2026-10-26.md`).
- Load explains 60% of the spread, and load's part of the steps gives the same ranking slope as the rest.
- It corrects #250's account of where batchgeneratorsv2 loses its steps: inside each training step, not in the
  loader.

## What changed

Nothing. This record is the review.

## Verified, no change needed

- **The record regenerates from the committed load table.**
  - Under OpenBLAS's Haswell kernel, `analyse` gives `reports/loop_host_load_2026-10-26.json` byte for byte.
  - Under this machine's AVX-512 kernel, 12 numbers differ in their last digits. The owner's test compares floats
    within a tolerance, as #251 does for #250's record, and passes here.
- **The report is bound to the record.**
  - The owner's tests bind both tables and the first-stage figures: 6.1 steps per point of busy, SE 0.27, F 536,
    60% of the spread, and 9.6 and 4.9 steps with %nice beside it.
  - They also bind the cycle counts (521 with a load; 448 in 95 groups over 8 days), the cross-record AUC slopes,
    and batchgeneratorsv2's and UAMT off's busy gaps.
- **The figures no test binds hold:**
  - 990 s against 10-minute samples is about 1.7 samples a cycle.
  - A mean %nice of 10 across the host's 4 CPUs is a nice job on 40% of one CPU.
  - `PST8PDT,M3.2.0,M11.1.0` is the US rule.
  - 05:19:55 PDT is 12:19:55 UTC.
- **The design is sound.**
  - Timestamps are the host's wall clock, read as in #253, so the load table and the record agree on every
    runner. `sadf` runs under the host's POSIX zone, because its date otherwise follows the runner's zone.
  - A cycle's load weights each sample by its interval's overlap with the cycle's 990 s. A cycle whose samples cover
    less than 80% of it has no load.
  - `samples()` drops the samples that two daily files share.
  - `main()` hashes and parses the same captured bytes, as the owner's review fixed.
  - `window` cuts at the 8th standing cycle, whenever the window holds one. The registration's `--until` (the 8th
    cycle's end) makes this the confirmation's own cut.
- **The correction to #250 is right.** `apply_augmentations` runs inside the training step, on the batch after it
  has moved to the GPU, as the owner's test checks. #250's script and report now say so, with the change marked.
- **The checks pass.**
  - Ruff 0.9.10 `check` and `format` are clean on the four changed Python files.
  - Mypy, with the pre-commit hook's flags, is clean over the whole repository (797 files).

## Observations for the owner (not changed)

- **The raw-sysstat regeneration cannot run here.** Its three tests skip because `local_data/sysstat` is absent,
  so the load table itself is checked only on the loop host. The report already asks for those files, and the
  window's, to be kept.
- **`sa25` can go a little before "early on 11-03".**
  - Its last sample is near 23:50 on 10-25, and `find -mtime +7` deletes a file once it is eight whole days old.
    So the first sysstat cleanup after 23:50 on 11-02 can remove it.
  - The plan says the files through the window's 8th standing cycle are already copied aside, so nothing is at
    risk.
- **UAMT off's busy gap includes batchgeneratorsv2's cycles in its reference.** The reference leaves out only UAMT
  off itself and batch 16. The effect is small: batchgeneratorsv2 is 26 cycles at −3.0 points.

## Verification

- **#252's and #250's test files** give 23 passed and 3 skipped (the raw-sysstat cases).
- **The guard set**, with these and the other loop analyses' tests, gives 611 passed and 9 skipped. The one failure
  is the standing `test_live_documents_stay_clean`, whose list is the same as on main.
- **Doc audit:** main's run differs from #253's only in five more cited paths, all present. This record adds no
  entries.
- **No independent review this round.** #252 needs no change.
