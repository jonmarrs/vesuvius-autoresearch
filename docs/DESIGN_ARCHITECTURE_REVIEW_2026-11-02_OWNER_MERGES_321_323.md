# Design and architecture review — the owner's #321, #322 and #323

Date: 2026-11-02. Baseline: `5880d7b2` (main after #323).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 05:12 UTC firing; main had not moved since #320 at the firings before it.
- **#321** ties October's ScrollGT cite to the newest tag made by the October deadline, so a later release does not
  turn a filed month's test red.
- **#322** is finding 101: villa's neural tracer's confidence stops, screened as a coverage lever. The registered
  rule closes that line (median G 0.083, under 0.10).
- **#323** is finding 102: the same stops screened by continuity. The registered rule keeps the line open (median
  gain of U 0.314, over 0.10).

No change was needed. This record is the round's only change.

## Verified, no change needed

- **#321.**
  - `_tags_made_by` keeps the `v*` tags created at or before the October record's `deadline_utc`, newest version
    first.
  - The new test builds a repository with tags on both sides of the deadline and passes.
  - The module gives 38 passed. 4 skip without the sibling ScrollGT and inkagree checkouts, including the cite test
    itself.
- **#322 (finding 101).**
  - **Timing.** The registration (`d2e912a7`, 06:55 PST) precedes the run (07:04–07:45). The script is
    byte-identical between the registration and the result commit.
  - **The verdict recomputes from the per-cube records.**
    - The median G of the ten held-out cubes is 0.0833.
    - The median premature share is 0.893 (P1).
    - The share is at least 0.8 times the cube's base rate on exactly 8 of the 10 cubes (P2; the two Scroll-5 cubes
      miss).
    - P3 misses, so the decision is "close".
  - **G is each cube's gap length over its covered length** in all 252 cube, tolerance and setting records.
  - **Code against definitions.** The reference walk, the split rule and the stop direction match the registered
    definitions.
  - **The report test binds every figure in the report.**
- **#323 (finding 102).**
  - **Timing.** The registration (`3a4821d2`, 14:28 PST) precedes the run (14:29–15:56). The script is unchanged
    after it.
  - **The verdict recomputes.**
    - The median gain of U is 0.314 (P1).
    - U_20's is 0.061 (P2 missed).
    - Fill and join's is 0.215, at least half of U's (P3).
  - **Gains.** Every recorded gain is its value over the cube's baseline ERLpen, minus 1, in all 273 rows.
  - **Gaps.** Each cube's union gap length equals finding 101's recorded gap length, at both tolerances on all 21
    cubes (the registration's gate 4).
  - **The edited labelling.** Joins never involve a zeroed trace, so zeroing after the union-find cannot undo a
    join. The first fill of a voxel wins. The bounded variants fill only within k and join only splits within k.
  - **The report test binds every figure in the report.**
- **The four new test modules** give 64 passed. They are outside the standard suite, like the earlier neural-tracer
  findings' tests.

## Observations for the owner (not changed)

- **#321: the cite test checks the whole draft, not the URL field.**
  - The draft's URL field cites `tree/v0.9.0`. #321's sentence says the test binds the cite to v0.9.1, the newest
    tag by the deadline.
  - The test passes because `scrollgt/tree/v0.9.1` appears in item 3's release list. A URL field naming any tag
    would pass while that list does.
  - The research entry was not submitted by the deadline, so this changes no filing. Which tag the field should name
    is the owner's call.
- **#322 and #323 cannot be re-run here.** The tracer's outputs and the ScrollGT checkout are not in this
  environment. The verdicts, identities and report figures above were checked against the committed JSON.
- **U is computed with ERL, which ignores merges the fill itself creates.** On the first held-out cube, U's
  labelling has one merge that its value ignores. As the registration says, that keeps U a ceiling on ERLpen. It is
  not the ERLpen of the edited labelling.
- **#323 reverses #322 on the same cubes.** Both reports say so: the second registration was written after, and
  because of, the first result. They agree that the finding screens a direction and supports no rule.

## Verification

- **#321's module:** 38 passed, 4 skipped. **The four neural-tracer modules:** 64 passed.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the seven new or changed Python files, and mypy is
  clean on both scripts. MYPY
- **The standard suite** SUITE
- **The test modules outside the suite** OUTSIDE
- **The doc audit** AUDIT
