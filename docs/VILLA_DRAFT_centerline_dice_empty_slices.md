# DRAFT, not posted: centerline_dice counts every predicted pixel on a slice with no ground truth as a hit

**Status: DRAFT, not posted; awaiting the user's go-ahead.** Found 2026-10-12 in this repo's
[training-step review](DESIGN_ARCHITECTURE_REVIEW_2026-10-12_TRAINING_STEP.md) (the loop's stored
`avg_centerline_dice` was 1.349). Patch: [`villa_pr_centerline_dice_empty_slices.patch`](villa_pr_centerline_dice_empty_slices.patch)
(+2/−1), applies cleanly to villa `origin/main` `4eecd08fd` (2026-10-13). Shaped by
[the contribution SOP](VILLA_PR_SOP.md): one defect, under 25 lines, pasteable evidence, no
recommendation, and **no AI-authorship markers in the villa commit or PR body**.

## Gate before opening (re-run on the day)

1. **Live at `origin/main`: yes** (`4eecd08fd`). `segmentation/evaluation/metrics/centerline_dice.py`
   still initialises `dist_transform = np.zeros_like(label, dtype=float)`; the file is unchanged since
   our pin `9afddaf0`.
2. **Not already fixed in a PR: checked for the 200 most recent PR heads only** (#1826–#2063 at
   2026-10-13: none changes `centerline_dice.py`). **Not checked: issues, and older open PRs.** Search
   villa issues and PRs for `centerline`, `cldice`, `centerline_dice` (with a positive control that the
   search returns `53c71e239`'s PR, "centersurface dice") before opening.
3. Patch applies to `origin/main`, +2/−1.
4. The evidence below runs from a villa checkout's root with only NumPy, SciPy and scikit-image.

## Title

`centerline_dice: no tolerance region on slices without a ground-truth skeleton`

## Body

`centerline_dice.compute` builds the tolerance mask from `dist_transform`, which starts as zeros and is
filled only on slices whose ground-truth skeleton is non-empty. On every other slice the distance stays
0, so `tolerance_mask` is all True there and every predicted skeleton pixel on that slice counts as a
match. A false positive on a slice with no ground truth therefore raises the score; the result can
exceed 1, and so can `centerline_sensitivity`.

`segmentation/evaluation/configs/recto.yml` and `recto-verso.yml` run this metric through `segmentation/evaluation/evaluate.py` on volumes,
where slices without ink are common.

From the repository root:

```python
import sys; sys.path.insert(0, "segmentation/evaluation")
import numpy as np
from metrics.centerline_dice import compute

gt = np.zeros((2, 32, 32), bool); gt[0, 10:14, 4:28] = True      # ink on slice 0 only
pred = gt.copy(); pred[1, 4:28, 10:14] = True                     # plus a stroke on empty slice 1
print({k: round(float(v), 4) for k, v in compute(gt, pred).items()})
```

| | centerline_dice | centerline_sensitivity | centerline_precision |
|---|---:|---:|---:|
| `main` | 1.3125 | 1.9091 | 1.0 |
| this PR | 0.6875 | 1.0 | 0.5238 |

The fix starts `dist_transform` at infinity, so a slice without a ground-truth skeleton has no tolerance
region and its predicted skeleton counts only in the denominators. On volumes where every slice has a
ground-truth skeleton nothing changes: all five returned values were identical, bit for bit, on 200
random 3×24×24 volumes.

Not changed: the skeletonization, the `surface=True` path's skeleton construction, and the return
keys.

## Notes for us (not part of the PR)

- Branch name suggestion: `fix/centerline-dice-empty-slices`.
- This repo's loop no longer reaches the bug (it scores each patch on its own and drops ink-free
  patches since the 2026-10-12 reviews), but `scripts/evaluate_villa_metrics.py` scores whole volumes
  through the pinned file and stays affected until the pin includes the fix.
