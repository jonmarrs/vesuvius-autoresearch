# What 153 upstream commits changed, for the things we depend on

**2026-08-31.** Reconnaissance after bumping the villa pin `ced62390e` -> `c935851c3`. The question
is narrow: does three months of upstream change invalidate anything we have measured, or open
anything up? Read-only.

## Churn is dominated by a move, not by new work on our track

```
volume-cartographer  61,109      spiral-fitting   14,490
vesuvius             55,803      foundation        9,014
dinovol              19,730      lasagna           2,309
```

`spiral-fitting`'s 172 files and 87,796 insertions are almost entirely the relocation of
`volume-cartographer/scripts/spiral/`. Comparing old path against new is the only way to see real
content change, and it is much smaller.

## The ink objective is unchanged, so our findings still apply

`get_ink_metrics.py` differs by **seven lines**, and none of them touch the metric:

```
-    try:
+    if 'fork' in multiprocessing.get_all_start_methods():
```

a multiprocessing start-method guard. `total_fg_pixels`, `overall_fg_fraction`, the line and column
scores, `COL_WIDTH_PX`, `LINE_PITCH_PX`, `fg_threshold` and `DEFAULT_MODEL` are all identical. So
`reports/duplicate_coverage_inflates_the_objective.md` and
`reports/objective_does_track_fit_quality.md` are statements about the current metric, not a stale
one.

`render_ink.py`, `tifxyz.py` and `lasagna/fit.py` are byte-identical between `5479453a` and
`c935851c3`, which is what makes the four seed arms comparable
(`docs/preregistration/2026-08-31_seed_spread_n4.md`, addendum 3).

## `satisfaction_metrics.py` was substantially reworked, and my reasoning about it predates that

**456 changed lines.** New: a packed evaluation path (`evaluate_patch_satisfaction_packed`,
`_patch_aligned_chunks`), a `satisfaction_atlas`, a profile system (`build_profile`, `dense_masks`
with a `strict` profile), and explicit `target_winding_indices` with `patch_winding_min/max` and
`dense_target_windings()`.

The winding indices are used as a **validity mask**, not an absolute-position comparison:

```python
target_set = target_winding >= 0
satisfied = target_set & (spiral_residual <= ...) & (scan_residual <= ...)
```

So the index says *whether a quad has a target at all*, which is consistent with @pmh47's statement
on villa#1621 that there is no absolute winding for a patch. **Reading the code does not show that
the metric can now see duplicate coverage, and it does not show it cannot.** That remains untested,
as `reports/duplicate_coverage_inflates_the_objective.md` says, and testing it still runs into the
reason `docs/preregistration/2026-08-28_winding_injection_conditional_on_acceptance.md` was shelved.

What this does change: any reasoning I did about satisfaction from the **old** implementation should
not be assumed to carry over. There is now a `strict` profile that did not exist in what I read.

**Our own numbers are unaffected.** The fits run `villa-spiral/spiral-fitting`, whose
`satisfaction_metrics.py` hashes to `d092a339`, identical to current upstream and not to the old
`a04825d9`. All four seeds' satisfaction figures come from the same current implementation.

## ink-detection is finished as a track

21 lines of churn across three months, and the body of it moved to `deprecated/`. Consistent with
`docs/... spiral-fitting is the live track`. Nothing here reopens the exhausted GT question.

## Nothing found that redirects current work

No new dataset, benchmark or metric appeared that bears on the seed-spread or duplicate-coverage
questions. The survey's value was negative and confirmatory: it ruled out the possibility that the
pin bump silently changed the instrument mid-experiment, which it could have.
