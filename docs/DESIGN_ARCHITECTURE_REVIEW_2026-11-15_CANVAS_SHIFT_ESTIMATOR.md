# Design and architecture review — #390's canvas-shift estimator

Date: 2026-11-15. Baseline: `bf6e959` (main after #424).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the hourly firings from 10:12 UTC on 2026-11-13 to 14:12 UTC on 2026-11-15. The work was done at
the start and the end of that span: between 11:13 UTC on 11-13 and 14:13 UTC on 11-15 the session could not run.

It reviews the part of **#390** that earlier rounds left: the estimator in `repro/sota_data/canvas_shift.py`. That
is `measure_shift`, which finds how far one window of an ink label canvas sits from the surface, and `fit_shift`,
which fits those shifts across windows as a constant, a line or an affine map. Rounds #162 and #163 covered the
module's two samplers.

The owner merged seven PRs while the session was down: #402, #408, #411, #421, #422, #423 and #424. They are merged
into this branch, they do not touch the estimator, and their review is left to later rounds.

## What changed

### A drift under one pixel collapses even after a term is dropped (`repro/sota_data/canvas_shift.py`)

`fit_shift` promises that "an axis whose fitted peak-to-peak is under one pixel collapses to the mean". With three or
more windows the fit first checks the full model against that rule, then drops any term whose own change is under
0.25 px and fits the rest again. It did not check the refit model. So the same 0.95 px drift across y came out two
ways:
- alone, it was a constant;
- beside a 0.20 px drift across x, the full model spanned 1.15 px, the x term was dropped, and the 0.95 px that
  remained was returned as a line.

The refit model now collapses to the mean as the full model does. The new test fails on the merged code. A 1.20 px
drift is still a line once the small term is dropped.

No registration covers the module.

### Fourteen guards of the estimator are now tested (`tests/test_canvas_shift.py`)

This round made 33 mutants of the estimator. One did not apply, because its text occurs twice. Of the other 32, the
module's tests killed 19. Eleven new test functions kill the other 13:
- **A weak match is not located at the default threshold.** A peak of about 0.4 is refused at the default 0.5 and
  accepted when 0.3 is asked for.
- **A shift is scored only on enough finite overlap**: half the window's finite pixels and at least 100 of them. A
  window with fewer than 100 finite pixels needs only half.
- **The correlation ignores each image's own level.** A copy offset by 100 still correlates at 1.
- **The sub-pixel step is a parabola's vertex**, and is held to one pixel when the three samples are not a peak.
- **A window within `max_shift` of any surface edge is refused**, at the top, left, bottom and right.
- **A window one pixel wide is refused.**
- **A drift under one pixel is a constant**: for two windows, for four windows, and when two terms that are each
  over the 0.25 px floor together wander by 0.8 px.
- **A fitted slope of half a pixel per pixel is refused**, for the y slope and for the x slope.
- **Centres near a tilted line get the per-axis fit.** The test's centres have an r squared of 0.94: over the 0.9
  threshold, and well under 1.
- **A region with a non-finite number is refused**, in any of its four fields.

The mutant that did not apply removes the slope bound of the per-axis fit. A case added to the slope test covers
that bound, and a mutant written for it fails the test.

## Verified, no change needed

- **The measurement reads as its docstring says.** A peak on the search boundary is not located. The centre is
  the mean of the window's pixel coordinates, and the level-0 values are the image values times `px_scale`, from
  the given origin. The module's tests kill a mutant of each.
- **The affine terms are assigned to the right names.** For `dy` the y slope is `sy` and the x slope is `cy`; for
  `dx` the y slope is `cx` and the x slope is `sx`. Swapping either pair fails the module's tests.
- **Two windows never produce cross terms**, and three or more on one row, one column or a tilted line get a
  warning. The module's tests cover each.

## Observations for the owner (not changed)

- **The overlap rule has a step at 100 finite pixels.** A window with 99 finite pixels can be scored on 49
  overlapping ones. A window with 100 to 199 needs 100, which for a window of exactly 100 is all of them, so a
  single hole in the surface patch stops that shift from being scored. The docstring states the half rule and says
  a window under 100 can still be scored; it does not describe the step.
- **`resample_to_tifxyz`, `correct_canvas` and the command line were not reviewed.** They are the rest of #390.

## Verification

- **The touched module.** `test_canvas_shift.py` gives 96 passed, against 70 on `bf6e959`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    two changed Python files.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 221 modules give the same 173 failing ids on `bf6e959` and on this branch.
- **The test modules outside the suite.** The 257 modules give the same 23 failing ids on `bf6e959` and on this
  branch, with 2,514 passed on both.
- **The doc audit**, run alone, lists the same unresolved references as on `bf6e959`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Both sets of failing ids are this container's: it has no villa checkout.

## A note on this round's work

- **The session was down for two days in the middle of the round.** The fix and most of the tests were written on
  11-13 against `a5e6663`. They were committed on 11-15, and the owner's seven merges were then merged in without
  conflict.
- **The baseline was run in the same checkout as the branch**, with the two changed files set back to main's for
  that run.
- **Still not reviewed:** the rest of #396, the rest of #390 named above, and the seven new merges.
- **The mutants are a sample** of the estimator's checks. The module's tests all passed here before the mutants
  were run.
