# Disconnected subrow components: hypothesis falsified, in the opposite direction

**2026-08-29.** Measured against the converged baseline fit. Artifact: `reports/subrow_disconnection.txt`.

## The hypothesis

Our baseline fit warned on 4,272 of 38,439 scored patches (11.1%): *multiple disconnected subrow
components; using only the component containing the center column*.

Reading `satisfaction_metrics.py` shows the mechanism. Subrows are linked where they overlap in `j`;
a BFS from the subrow containing the centre column propagates `branch_offset`; unreached subrows keep
`branch_offset is None` and the scoring loop skips them:

```python
for subrow in all_subrows:
    if subrow['branch_offset'] is None:
        continue
    satisfied_quad_mask[i, j_min:j_max] = in_band
```

Skipped quads never enter the numerator but remain in `in_roi_valid_quad_mask`, the denominator. So
they are unsatisfied regardless of geometry, and the expectation was that warned patches would score
**lower**.

## The result

They score **higher**, substantially, and in every area decile.

| group | n | mean fraction | median | fraction == 0 | mean area |
|---|---:|---:|---:|---:|---:|
| warned (disconnected) | 4,272 | **0.8751** | 0.9968 | 0.1% | 464,325 |
| unwarned | 34,167 | **0.7909** | 0.9935 | 3.7% | 473,761 |

Unwarned minus warned is **-0.0842**. Controlling for size by comparing within area deciles, the gap
survives in all ten, ranging -0.128 to -0.048. Deciles where unwarned scores higher: **0 of 10**.

The size confound was the obvious objection (a patch with more rows has more chances to contain a
disconnected subrow), and it is not the explanation. Mean areas are nearly identical to begin with.

## The mechanism that explains the reversal

The `fraction == 0` column: **3.7% of unwarned patches score exactly zero, against 0.1% of warned
ones.** That is a 37x difference and it points at selection rather than at scoring.

To emit this warning a patch must get far enough to have a valid centre subrow, build multiple
subrows, and run the BFS. A patch that is degenerate, tiny, or has no valid centre column never
reaches that point, so it cannot be warned, and it also tends to score zero. The warning is
therefore a **marker of patches with enough structure to be scored at all**, and that selection
dominates whatever the skipped quads cost.

The cost of skipping is presumably still real per-patch. It is simply not detectable at population
level, because the population that can produce the warning is healthier to begin with.

## What this does and does not establish

**Establishes:** disconnected subrow components are not a hidden drag on the reported satisfaction
numbers. The 11.1% warning rate is not evidence that the metric is understating fit quality, and the
conservative skip is not costing what it appeared to.

**Does not establish:** that skipping is free. A per-patch measurement, scoring the same patch with
and without the disconnected components counted, would isolate that; this population comparison
cannot.

**Does not establish causation at all.** The warning is not randomly assigned. The decile control
addresses size only, and any other property that both causes disconnection and raises satisfaction
would produce exactly this pattern. The `fraction == 0` asymmetry is a strong hint at such a
property rather than a proof of one.

## Why this is written up

It is a negative result on a hypothesis I formed, stated publicly to Jon as the most promising
unexamined observation from our own run, and then measured. The measurement said the opposite. That
is the whole value: had it not been checked, "11.1% of patches have geometry silently dropped by the
metric" is exactly the kind of plausible, well-formed, wrong claim this project has spent two days
retracting.

Nothing here goes to villa. It is a null about their code that reads as a defect only if you stop
before measuring it.

## Limits

One fit, one scroll, one z-ROI [13056, 18432), three inputs disabled
(`fibers`, `tracks`, `pcl_drawn_control_points`). Warning counts come from parsing the run log, and
patch indices are positional into `satisfied_fitted.json`.
