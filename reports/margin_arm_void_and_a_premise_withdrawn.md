# MARGIN0 is void, and the premise behind it is withdrawn

**2026-09-01.** Arm registered in `docs/preregistration/2026-09-01_output_margin_and_outer_duplication.md`.
**The verification condition could never have fired, and the premise it tested was wrong.** No
conclusion about the margin is drawn, and a claim in an earlier report is withdrawn.

## What the arm returned

| fit | gap>=2 | as fraction | satisfied area | total_fg |
|---|---:|---:|---:|---:|
| baseline01 | 10,345 | 0.0897% | 0.8398 | 240,088 |
| seed02 | 11,895 | 0.1029% | 0.8404 | 194,634 |
| seed03 | 12,040 | 0.1042% | 0.8382 | 221,576 |
| seed04 | 11,319 | 0.0980% | 0.8399 | 250,936 |
| **MARGIN0** | 11,154 | **0.0965%** | 0.8410 | 248,365 |

MARGIN0 sits **inside the honest range on every measure**. It is indistinguishable from an ordinary
fit.

## Why that is not evidence about the margin

The registered verification was that the output winding range narrows from `[10, 130)` to about
`[10, 126)`. It printed `[10, 130)`, unchanged. The override was applied, since `fit_spiral.py:232`
raises `KeyError` on unknown override keys and the run was clean. The observable was simply
insensitive:

```python
# spiral_helpers.py:1372
max_winding_idx = min(max_winding_idx, cfg['shell_outer_winding_idx'])
```

and `config.py:489` sets `shell_outer_winding_idx = 130` as a **default constant**. The printed
range is clamped at 130 whatever the margin does, so the condition could not fire in either
direction. **The arm is void**: it neither supports nor refutes the margin hypothesis.

## The premise is withdrawn

`reports/duplicate_coverage_is_an_outer_winding_phenomenon.md` and the pre-registration both argued
from `output_winding_range = (..., max_w + 1 + margin)` that, with output `[10, 130)` and margin 4,
the patch data must end at **w125** and w126 to w129 must be extrapolated past it. From that I
computed "52.5% of overlapping cells involve an extrapolated winding".

**That arithmetic is invalid.** The output bound is the configured constant 130, not `max_w + 5`, so
it says nothing about where the data ends. `max_w` could be 129 or beyond and produce the same
output. Nothing in the fit logs records the observed patch winding maximum, so **I do not know where
the data ends**, and the 52.5% figure is withdrawn: it was computed against a boundary I inferred
from a formula that the clamp overrides.

## What survives

**The measurement stands**: duplicate coverage concentrates in the outermost windings, median wmax
126, 79.9% involving a winding at or beyond w120, reproducible across five fits with median radius
varying by 13 voxels. That is measured, not inferred.

**The explanation is again unknown.** "Boundary effect" was already labelled a hypothesis; the
specific extrapolation mechanism is now removed from the table. What is left is the observation
without a cause.

## The mis-specification pattern, three for three

Every verification condition I have registered for these fit arms has been wrong:

1. MINSPACE0: required a loss term's *name* to vanish. Worked by luck, since that term's logging
   happens to be weight-gated.
2. DENSESPACE0: same condition, but that term's logging is **not** weight-gated, so it read as a
   failure when the manipulation had in fact worked. The correct observable was the logged *value*.
3. MARGIN0: required a printed range to narrow, when that value is **clamped by a separate config
   constant** and cannot respond.

Each time the condition was written from a plausible reading of the code rather than from checking
what the observable actually does. The fix is not a better guess: it is to verify the observable
responds to the manipulation **before** spending 90 minutes of GPU on the arm, which none of these
did.

## Not continuing

Under the addendum-3 stopping rule I am not trying further config knobs here. The outer-winding
concentration is a measured phenomenon with no established cause, and that is where it is left.
