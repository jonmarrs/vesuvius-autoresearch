# placement-check

**A registration is only correct if agreement peaks at zero shift. This is the ten lines
that check it.**

```bash
python placement_check.py my_label.png reference.png --max-offset 8
```
```
peak at (dy=31, dx=-8), offset 32.0 px; dice 0.5901 at zero, 0.6878 at peak
  agreement improves +0.0977 when shifted, which it should not for a correctly placed label
FAIL: offset 32.0 px exceeds 8 px
```

Numpy only. One function. Exits non-zero so it can gate a pipeline.

## Why this exists

We shipped a ground-truth benchmark whose registration reported a **median correspondence
residual of 8 voxels**. The label was displaced by **1766**.

Both numbers were true. A residual measures how much individual correspondences *scatter*;
it says nothing about where the result ends up. We had quoted the residual as evidence of
correct placement, which it never was.

Everything scored against that label read at chance, including models that were reading
fine. The published conclusion, "no model reads held-out," was an artifact of our own
misregistration. Corrected, the same models score 0.73 to 0.75 ROC-AUC against a 0.52
floor. They had been reading the whole time.

The error survived a residual gate, a 4-way orientation check, a text-line periodicity
check, code review, and a public leaderboard, for a month. It was found by an outside
reviewer saying our alignment example did not show the alignment working.

Nothing tested placement. That is the whole story.

## Usage

```python
from placement_check import placement_offset

r = placement_offset(label, reference)      # 2-D arrays, same shape
if not r.passed(max_offset=8):
    raise SystemExit(f"label is {r.offset:.1f} px out of place at ({r.dy}, {r.dx})")
```

`reference` is whatever the label should agree with: a model prediction, another
annotator's labels, a segmentation mask. It does not need to be good, only independent and
better than chance. A weak reference widens the peak; it does not move it.

Bool arrays are used as-is; anything else is thresholded at `>127`.

## Choosing a threshold

There is no universal number. Convert the offset into units that mean something for your
task. If you analyse in N×N windows, an offset approaching N means a prediction and the
label it is scored against **need not overlap at all**, and the score is measuring
something else. Well under a window is tolerable smearing.

For us: a 512 µm analysis window, a measured floor of ~0.31 mm imposed by genuine
differences between two scans of the same object, and a gate set just above that floor at
~0.46 mm. We wrote down the derivation next to the constant, because a threshold chosen to
let your own data through is not a gate.

## Three things worth knowing

**It tells you two artifacts disagree, not which one moved.** Find out which before
"correcting" anything. Fitting a shift so a number improves is how a registration bug
becomes a permanent fudge factor.

**Do not let it pass on garbage.** Given an already-boolean mask, an earlier version of
this applied `> 127`, produced an all-False image, and scored a *perfect* zero offset. A
check that returns "fine" for empty input is worse than no check. That case now raises, and
so does a peak pinned to the search boundary, which under-reports.

**Prove it can fail.** Before trusting it, shift your label by a known amount and confirm
it is detected. We found the bug above with a check we had never seen fail; a test that has
never failed is not evidence.

## Provenance

Extracted from [vesuvius-autoresearch](https://github.com/jonmarrs/vesuvius-autoresearch),
where it gates both the benchmark-target and training-data registration paths. Full
write-up of the failure, including two further instances of the same pattern:
[`registration_offset_2026-08-07.md`](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registration_offset_2026-08-07.md).

MIT.
