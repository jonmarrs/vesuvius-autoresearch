# DRAFT, NOT READY TO POST: centerline_dice counts every predicted pixel on a slice with no ground truth as a hit

**Status: not postable yet.** villa's `CONTRIBUTING.md` (checked at `origin/main` `4eecd08fd`, 2026-10-13)
requires things only the owner can supply, and this draft must not go up without them:

1. **Real scroll data, before and after.** "Bugfixes or improvements must be run on real scroll data. Synthetic
   or toy examples are not accepted", plus "a screenshot of the error ... and the script/tool running without
   error afterward". The two-slice reproduction below is supporting detail, not the proof.
2. **A motivation section in the owner's words**, saying what they were doing when the number came out wrong.
3. **Human-written commentary.** "Any LLM generated PR must be accompanied by human-written commentary explaining
   why this PR is relevant or useful." This defect was found during an LLM-assisted review of this repository;
   villa says it may close LLM "fishing expeditions", so the PR has to stand on the owner's own use of the metric.
4. **villa's PR template** (`.github/pull_request_template.md`), including its checkbox "I personally verified
   that the example and proof above were produced by this PR on the stated data". Only the owner can tick it.
5. **The issue and PR search** in the gate below.

[The contribution SOP](VILLA_PR_SOP.md) also applies: one defect, under 25 lines, no AI-authorship markers in the
villa commit or PR body.

Patch: [`villa_pr_centerline_dice_empty_slices.patch`](villa_pr_centerline_dice_empty_slices.patch) (+2/−1),
applies cleanly to villa `origin/main` `4eecd08fd`.

## Gate before opening (re-run on the day)

1. **Live at `origin/main`: yes** (`4eecd08fd`). `segmentation/evaluation/metrics/centerline_dice.py` still
   initialises `dist_transform = np.zeros_like(label, dtype=float)`; unchanged since our pin `9afddaf0`.
2. **Not already fixed in a PR: checked for the 200 most recent PR heads only** (#1826–#2063 at 2026-10-13: none
   changes `centerline_dice.py`). **Not checked: issues, and older open PRs.** Search villa issues and PRs for
   `centerline`, `cldice`, `centerline_dice`, with a positive control (the search should find the PR that
   introduced `53c71e239`, "centersurface dice").
3. Patch applies to `origin/main`, +2/−1.
4. Real-data before/after produced (below) and attached.

## Real-data evidence: how to produce it on the GPU host

Where the number was first seen on real data: this repository's loop scored validation batches of
`PHercParis2Fr143` patches with villa's `centerline_dice`, passing each batch as a stack of slices, some of them
ink-free. The stored incumbent records `avg_centerline_dice` **1.349** (`best_model.pt`, `val_f1` 0.468) — a
Dice above 1. That is the motivating encounter; the proof should come from villa's own pipeline:

* **Preferred:** run `segmentation/evaluation/evaluate.py` with `segmentation/evaluation/configs/recto.yml`-style settings (keep only the
  `centerline_dice` metric) on one real label/prediction volume pair, once at `origin/main` and once with the
  patch applied. Record any per-volume `centerline_dice` or `centerline_sensitivity` above 1 before, and the
  values after. Screenshot both runs.
* **Fallback:** the same stack-of-patches call the loop made, on real Fr143 patches and a real prediction, before
  and after.

## Title

`centerline_dice: no tolerance region on slices without a ground-truth skeleton`

## Body (villa template; bracketed parts are the owner's to write)

**In one sentence:** centerline Dice no longer rewards predicted strokes on slices that have no ground truth, so
it stays in [0, 1].

**One real example:** Starting with [real label/prediction volume], I ran `segmentation/evaluation/evaluate.py`
with the `centerline_dice` metric, and it produced [value above 1 / inflated value].

**Before:** `dist_transform` starts as zeros and is filled only on slices whose ground-truth skeleton is
non-empty. On every other slice the distance stays 0, so `tolerance_mask` is all True there, and every predicted
skeleton pixel on that slice counts as a match. A false positive on a slice with no ground truth raises the score;
`centerline_dice` and `centerline_sensitivity` can exceed 1.

**After this PR:** `dist_transform` starts at infinity, so a slice without a ground-truth skeleton has no
tolerance region; its predicted skeleton counts in the denominators only.

**Proof:** [screenshots of the real-volume run before and after]

**Why / where this is useful:** [owner: who compares models with this metric and what the inflated value
misled]

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

Patch: `segmentation/evaluation/metrics/centerline_dice.py`, +2/−1 (a one-line initialisation change and a
comment). Unchanged: the skeletonization, the `surface=True` skeleton construction, and the return keys.

Minimal reproduction of the mechanism (supporting detail; not a substitute for the real-data proof), from the
repository root:

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

On volumes where every slice has a ground-truth skeleton nothing changes: all five returned values were
identical, bit for bit, on 200 random 3×24×24 volumes.

## Notes for us (not part of the PR)

- Branch name suggestion: `fix/centerline-dice-empty-slices`.
- This repository's loop no longer reaches the bug (it scores each patch on its own and drops ink-free patches
  since the 2026-10-12 reviews), but `scripts/evaluate_villa_metrics.py` scores whole volumes through the pinned
  file and stays affected until the pin includes the fix.
