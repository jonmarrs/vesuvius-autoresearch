# Pre-registration: does the output-winding margin cause the outer duplication?

**Written 2026-09-01, before the arm is fitted.**

## Why this is not a violation of the stopping rule

`docs/preregistration/2026-08-31_satisfaction_vs_fit_produced_duplication.md` addendum 3 registered:
"if this arm also returns a null, I will not keep zeroing loss weights until something moves". That
rule ended the search for a way to **induce** duplication, and it stands: no third loss weight will
be tried for that purpose.

This asks a different question with a different mechanism. `reports/duplicate_coverage_is_an_outer_winding_phenomenon.md`
established that the *existing* 0.09 to 0.10% duplicate coverage concentrates in the outermost
windings and offered a boundary effect as an untested explanation, explicitly naming the missing
test. This is that test. It explains a measured phenomenon rather than hunting for a new one.

## The mechanism under test

`spiral_helpers.py:989` computes the output range as

```python
output_winding_range = (max(min_w - margin, first_winding), max_w + 1 + margin)
```

with `output_winding_margin = 4`. Our fits output `[10, 130)`, so the observed patch data ends at
**w125** and **w126 to w129 are extrapolated beyond it**. Those windings are constrained by no
patch data on their outer side.

Measured on `baseline01`'s 10,345 overlapping cells:

```
52.5% have their OUTER winding beyond w125   (involves extrapolation)
11.9% have BOTH windings beyond w125          (entirely extrapolated)
median wmax 126
```

So extrapolation is implicated in about half the cells and cannot be the whole story.

## Arm

**MARGIN0**: identical to `baseline01` except `"output_winding_margin": 0`. Everything else
unchanged, including both spacing weights at their defaults.

## Predictions, fixed now

1. **The output winding range narrows** to roughly `[10, 126)`, confirming the change took effect.
   This is the verification condition, and unlike the last two it is checked on a value the fit
   prints directly rather than on a loss term's logging.
2. **Full-fit gap>=2 falls to between 0.03% and 0.07%**, from the honest 0.0897 to 0.1042%. That is
   the range implied if the ~52% of cells involving an extrapolated winding largely disappear and
   the rest remain.

## Decision rule

* `gap>=2` in **0.03 to 0.07%**: extrapolation explains roughly the share predicted. Supported.
* `gap>=2` **below 0.03%**: extrapolation explains *more* than the cell counts implied, so the
  remaining cells depended on the extrapolated windings too.
* `gap>=2` **at or above 0.0897%**, the honest range: **extrapolation is NOT the cause** and the
  outer-winding report's boundary explanation is wrong, not merely unproven.
* satisfied area outside 0.8382 to 0.8404: the arm changed fit quality as well, and the duplication
  result is confounded rather than clean.

## Limits

One fit, one seed, one ROI. Removing the margin also removes real output surface, so the comparison
is not perfectly like-for-like: fewer windings means fewer opportunities for overlap regardless of
mechanism. **The count must therefore be read as a fraction of occupied cells, not as an absolute**,
and even then a narrower output is a weaker test than a fit whose *data* ends elsewhere. That
stronger test is still not run.
