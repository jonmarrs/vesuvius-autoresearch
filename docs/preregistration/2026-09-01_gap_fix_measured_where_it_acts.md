# Pre-registration: does the gap-expander fix help ink in the windings it actually affects?

**Written 2026-09-01, before either render.** No outer-winding ink render exists for any fit.

## The flaw in my own measurement

`reports/gap_expander_fix_improves_the_fit.md` reports that raising
`model_gap_expander_num_windings` 130 -> 133 improves `satisfied_area` by 7 to 9 sd, while
`total_fg_pixels` moved only +2.5%, inside its 21.7% floor, and I concluded the ink effect was
"not established".

That conclusion was correct but the measurement behind it was **aimed at the wrong place**. The
shortfall concerns losses sampling out to `shell_outer_winding_idx = 130`, so whatever it affects is
in the **outermost** windings. Every ink render in this work covers **w010 to w019**, the innermost
ten. The measurement was blind to the region the change acts on, and would have read as null whether
or not the fix helps there.

This is the same class of error as the three mis-specified verification conditions: an observable
chosen from a plausible reading rather than from asking where the manipulation can express itself.

## Arms

No new fits. The meshes exist; only the render and score are needed.

* **BASE-OUTER**: `baseline01`, windings **w120 to w129**.
* **GAP-OUTER**: `gap133`, windings **w120 to w129**.

Identical render and scoring settings to every previous arm, tooling pinned to villa `5479453a`.

## Predictions, fixed now

1. Both render non-blank (`p95 > 0`). The outer windings are data-supported
   (`reports/the_outer_boundary_is_configured_not_data.md`), so a blank strip would mean a render
   fault, not an absence of ink, and would void the arm.
2. **I do not predict the direction of the ink difference.** The mechanism is a reading of the code,
   and I have been wrong three times about what an observable does. Predicting now would invite
   reading the result to match.

## Decision rule

This is a **same-fit-pair comparison across two different fits**, so the applicable floor is the
different-fit one: `2*CV` = **21.7%** on `total_fg_pixels`.

* `|dT| >= 0.217`: a real difference in the outer windings, in whichever direction it falls.
* `|dT| < 0.217`: **uninterpretable, exactly as the inner-winding measurement was.** Reported as
  "still not established", NOT as evidence of no effect. With one fit per arm this is the likely
  outcome and I am recording that expectation now so a null is not later dressed up as a finding.

A single pair cannot clear a 21.7% floor except for a large effect. The honest value of this arm is
that it measures the right region at all; if it returns another null, the correct conclusion is that
answering the question properly needs three seeds per arm, which is six fits and about nine hours.

## Limits

One fit per arm, one dataset, one ROI. The outer ten windings are also where duplicate coverage
concentrates (median wmax 126), so the region is atypical in a way that could affect ink scoring
independently of the config change.
