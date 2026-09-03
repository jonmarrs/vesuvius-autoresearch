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

> **Update 2026-09-02, after bumping the pin to `908aa7f06`: this equivalence is now PARTIALLY
> BROKEN.** Re-checked against the new pin:
>
> | file | `5479453a` vs `908aa7f06` |
> |---|---|
> | `spiral-fitting/render_ink.py` | identical |
> | `spiral-fitting/tifxyz.py` | identical |
> | `spiral-fitting/get_ink_metrics.py` | identical |
> | `lasagna/fit.py` | **DIFFERS** |
>
> `lasagna/fit.py` gained `from dtypes import torch_float_hi` (villa #1639, lasagna on the mps
> backend, which also adds `lasagna/dtypes.py`). That file is the **flatten** step, so it determines
> the mesh geometry a render is scored on -- the one place a silent difference would move
> `total_fg_pixels` without touching the scorer.
>
> **No existing arm is affected**, because work dirs are built from the separate `villa-spiral`
> checkout at `5479453a`, not from this submodule. But the two trees are no longer interchangeable on
> the render path, so the shortcut of treating them as one is dead: a work dir built from the
> submodule would flatten with different code from every arm measured so far.
>
> **The divergence is wider than the four files this survey originally checked.**
> `scripts/check_villa_render_path.py` diffs every executable file under the trees
> `setup_workdir.sh` actually extracts, and finds **15 changed** between `5479453a` and `908aa7f06`,
> not one: `lasagna/fit.py` on the hot path, plus `model.py`, `fit2tifxyz.py`, `fit_data.py`,
> `cyl_sdf_volume.py`, `init_shell_index.py`, `approval_inpaint.py`,
> `labels_to_winding_volume.py`, `predict3d_holescan.py`, `tifxyz_lasagna_dataset.py`,
> `train_tifxyz.py`, two lasagna tests, a prefetch script, and
> `vesuvius/src/vesuvius/tifxyz_label_transfer/io.py`. Several are squarely on the flatten path.
> Hand-checking a named list of files was the weakness; the checker enumerates the trees instead and
> exits nonzero, so it can gate a bump.
>
> **Second bump, 2026-09-02 21:22: `908aa7f06` -> `9daa477e0`** (villa #1684, "make cylindrical as
> fast (or faster) than cartesian"). The render-path gate fires, and for the first time the changed
> files are in **`spiral-fitting/` itself**: `flow_fields.py`, `flow_triton.py`, `transforms.py`,
> plus two added files (`bench_cylindrical_rk4.py`, `tests/test_cylindrical_triton.py`). Those are
> FIT-side; the four hot-path files are still byte-identical to `908aa7f06`:
>
> | file | `908aa7f06` vs `9daa477e0` |
> |---|---|
> | `spiral-fitting/render_ink.py` | identical |
> | `spiral-fitting/get_ink_metrics.py` | identical |
> | `spiral-fitting/tifxyz.py` | identical |
> | `lasagna/fit.py` | identical |
>
> **The second-look study running at the time is unaffected**, and provably so rather than
> hopefully: its fits and renders both come from the separate `villa-spiral` checkout at `5479453a`,
> which was deliberately not fetched. The submodule is used only by this repo's tests.
>
> Full-suite verification was deferred while a 26GB render was in flight, and **completed
> 2026-09-03 14:23 once the second-look study finished: 822 passed, 1 skipped, 0 failed** in 4m21s.
> Both the `908aa7f06` and `1ee7f94d3` bumps are now verified by the full suite, not only by the
> gate. (Suite grown 784 -> 823 over two days, all of it tests added beside the tooling written for
> the outer-winding work.)

> **Third bump, 2026-09-03 09:40: `9daa477e0` -> `1ee7f94d3`** (three commits: VC3D line-annotation
> fixes #1685, plus two website edits). The gate returns **render path identical** -- nothing under
> `spiral-fitting`, `lasagna` or `vesuvius/src` moved, so work dirs from either ref are
> interchangeable and no equivalence check is owed. These were the first upstream moves caught by
> `scripts/watch_villa_upstream.sh` rather than by asking; all three arrived pre-gated, and the
> correct response to each was visibly nothing.
>
> Taken while the second-look study was mid-flight, which is safe for the same reason as the last
> two: fits and renders come from the separate `villa-spiral` checkout at `5479453a`, deliberately
> not fetched. Full-suite verification stays queued behind the study.

> **Bump verification, completed 2026-09-02 18:32.** The bump commit deferred the full suite because
> a 26GB render was in flight and said so rather than implying a clean bill of health. It has now
> run on an idle box: **802 passed, 1 skipped, 0 failed** in 4m29s, against 803 collected. Nothing
> the `908aa7f06` bump changed breaks anything here, which is the check the previous 153-commit bump
> failed (19 collection errors). The deferred claim is closed.

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
