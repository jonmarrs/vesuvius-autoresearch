# Design and architecture review — the owner's #229, finding 99

Date: 2026-10-25. Baseline: `b808f3d3` (main after the owner's #229).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 07:12 UTC firing. The 05:13 and 06:13 firings found main unmoved after #228. #229 reports
finding 99 (`reports/neural_tracer_heading_residual.md`), which is exploratory. It asks why villa's neural tracer
still drops seed dots with the scan around each cube.
- It classifies every seed dot of the 256³ cubes, and a 2,000-dot sample of each 512³ cube, by villa's own checks.
- Every classified dot that fails does so at villa's last check, the 35° test of the CT's axis against the dot's
  direction.
- Per cube, the dropped share tracks the share of dots in sheets tilted more than 45° from vertical: Pearson r 0.98.

## What changed

- **Finding 97's open question now points to its answer.**
  - Finding 97 said its two held-out Scroll-5 cubes still drop 0.266 and 0.353 of their seed dots, and that the
    cause was untested.
  - Finding 99 classifies every dot on both cubes. A dated note in `reports/neural_tracer_ct_context.md` now cites it:
    - every failing dot fails the 35° test;
    - 0.78 and 0.84 of their dots lie in sheets tilted more than 45°, against at most 0.04 on any in-sample cube.
  - `tests/test_neural_tracer_heading_residual_report.py` binds the note's figures to finding 99's JSON.
- **E2's verdict is now checked at its stated scope.**
  - E2, in the script, names no cubes. It expected that, at the dropped dots near the ground truth, the presence
    direction would be the further from the tangent on most.
  - The report marks it failed, "the other way round". The test checked that only on the two held-out Scroll-5
    cubes.
  - Over all 21 cubes it fails too. Pooled, the CT's axis is the closer on 0.12 of the 1,347 such dots, and it is the
    closer on fewer than half of them on 18 of the 21 cubes.
  - The test now checks the pooled share and the majority of cubes. The three cubes where the CT's axis is the closer
    on most are in sample, with 3, 8 and 12 such dots.
- **The report test is `ruff format` clean again.**
  - #229's last commit (`6d846c84`) left seven statements in a form that `ruff format` rewrites.
  - Pre-commit's ruff-format hook would have rewritten the file on the next commit that touched it.
  - The file is now formatted with ruff 0.9.10, the pinned version. No logic changes.

## Verified, no change needed

- **The run is the runs it explains.** The owner's tests check, from the JSONs:
  - villa's tile_dots re-derives each run's dot count on all 21 cubes;
  - pass 2 gives pass 1's counts;
  - villa's own `_seed_heading` agrees on the first 50 dots of each cube, and its sheet normal is the classifier's;
  - all 5,663 written seeds checked match a dot and pass, including 300 on each 512³ cube, each of which wrote more.
  The starting figures are findings 97 and 98's records.
- **The classifier is villa's code at the pinned revision.** This repository pins villa at ccb431818, the revision
  the JSON records. Read against that checkout:
  - the four reasons are villa's, in villa's order: the CT window, the sheet normal (at the seed headings' 1e-6
    gap), the family's axis, then the 35° test;
  - the normal is in world xyz (the tensor is reversed to array order for the eigensolve and back), so the tilt is
    measured from the scroll's z axis;
  - an H fiber's axis is the cross product of z and the normal, the sheet's horizontal line, and a V fiber's is z
    projected into the sheet, as the report says.

  The owner's constants test passes here against that checkout.
- **Timing:**
  - pass 1's script and expectations were committed at 19:59 PDT on 2026-10-24, before its 20:48 run;
  - its result was committed at 21:32, after the run ended at 21:31;
  - pass 2's script, with the 45° line, is the script on main apart from one docstring.
- **E1 and E3's verdicts:**
  - E1 held: every failing dot on the two held-out cubes is `disagree`.
  - E3 is judged by the classification's share of all dots, as its wording says. By the runs' own counts, which count
    only the dots each run offered, the two Scroll-3 cubes drop 0.074 and 0.088, below 0.10. The report's table shows
    both.
- **Every figure in the report** is computed by the owner's tests from the JSONs.

## Observations for the owner (not changed)

- **Pass 2's run began a minute before its commit.** The report times the run from 21:37, and its commit is dated
  21:38. Nothing here records the file that run used. The committed script differs from main's only in a docstring.
- **The skeleton hashes cannot be checked here.** ScrollGT's targets are not in this container, so that test skips.
  The report's review section says all 21 match ScrollGT v0.9.0.
- **The classification cannot be rerun here.** It reads findings 97 and 98's runs, padded CTs and checkpoint from
  the owner's machine, as those findings' scripts do.

## Verification

- **Tests:** finding 99's two test files, with findings 96–98's, give 80 passed and 3 skipped. The skips are the
  ScrollGT hashes, finding 91's run records and one villa file absent from this container's checkout.
- **Perturbations:** each of six edits fails a test:
  - three figures and one threshold in the note;
  - the CT's axis made the closer on every cube but the held-out two;
  - one held-out dot moved to `edge`.
- **Ruff** 0.9.10 `check` and `format` are clean on the test file.
- **Doc guards, the withdrawn-claims ledger, the suite guard, the filing and form-answer tests, and finding 96–99's
  tests:** 569 passed and 9 skipped.
  - The one failure is `test_live_documents_stay_clean`, which lists villa paths absent from this container's villa
    checkout.
  - Its list is the same before and after this change.
- **Doc audit:** #229 adds no entries, and neither does this branch.
- **No independent review this round.** The change is a dated note and two test checks, each checked by
  perturbation.
