# Design and architecture review — the owner's #219, #220, #224 and #225 (finding 98)

Date: 2026-10-24. Baseline: `2ac60b5f` (main after the owner's #219, #220, #224 and #225).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 20:12, 21:12, 22:12 and 23:12 UTC firings. Rounds since #222 found #223 (the retry probe's
failure contract) and #216 and #221 (findings 96 and 97 in the October filing draft) sound, with no change.
- **#220** pre-registers the CT-context test on the eleven 512³ cubes.
- **#224** reports its result, finding 98 (`reports/neural_tracer_ct_context_512.md`). With the scan around each
  512³ cube, villa's neural tracer keeps its seeds and its coverage rises 1.19–1.35×. All four predictions held on
  both sets.
- **#225** folds finding 98 into the October filing draft and cites ScrollGT v0.9.0.
- **#219** withdraws #206's octant tracing-context registration, which never ran.

## What changed

- **One submission claim was matched as text, not computed.**
  - The filing draft says ScrollGT v0.9.0's new row, the neural tracer with the scan around each cube, is "first
    on merge-penalized ERL on 10 of the 21, against 8".
  - That is a ranking against every entrant (connected components, #1934's generator and our tracer), not just
    ours. #225's test asserted the sentence, but nothing computed it.
  - It is true. `tests/test_filing_2026_10_numbers.py` now computes it from finding 91's comparators and findings 97
    and 98's padded rows, at tolerance 2. The test also checks that the new row is above the cube-only row it sits
    beside, on every cube.

## Verified, no change needed

- **Finding 98's decision logic is the registration's.**
  - P1: below finding 91's share on every cube, and below 0.05 in sample.
  - P2: a rise on every cube and a median of at least 1.15 per set.
  - P3: ahead on all eleven at tolerance 4, and at tolerance 2 ahead on Scroll 3 and behind on Scroll 5.
  - P4: below 0.10 on at least six of the eight Scroll-3 cubes.
  - The per-set readings follow the registered table.
- **The registration's arguments are the evidence.** Recomputed:
  - finding 97's median factor 1.95 as about the 0.63th power of 1/0.348, giving about 1.36 for 1/0.618;
  - the 0.854–0.945 reachable share;
  - Scroll 5's 0.43–0.48 of our tracer at tolerance 2, which needs 2.1–2.3× to overtake.

  The owner's tests bind each.
- **Finding 98's tests already follow round 116's pattern.** They check the copied rows against the committed
  findings, and recompute both stored verdicts.
- **Timing:**
  - the registration was committed at 05:53 PDT, and the slab-wise conversion at 05:56, before the 06:09 download;
  - the conversion change keeps the voxels and is tested against finding 97's conversion.
- **The 21-cube totals:**
  - with the scan, ahead of our tracer on 19 of 21 at tolerance 4 and 10 at tolerance 2;
  - with the cube alone, 11 and 8.

  Recomputed, and bound by the owner's test.
- **#225's other figures** are computed from the JSONs. Each of nine perturbations to them fails a test.
- **#219's withdrawal:**
  - its figures are finding 97's: 0.002–0.010 against 0.542–0.678, and ahead on 6 of 8 at tolerance 4;
  - the chain and script stay as registered, with a header saying a run now is outside any registration.
- **#220's chain uses #217's loop guard.** The guard test finds it by glob and passes.

## Observations for the owner (not changed)

- **The re-fetch helper is not in the repository.** Finding 98 says the server interrupted the download twice, and
  an unregistered helper re-fetched the missing slices. Every padded CT's core is checked against finding 85's array,
  but the 128-voxel margin around it is not.
  - A slice the helper fetched in the margin is not checked against anything.
  - The margin is the manipulation: it gives the seed windows near the faces their CT.
  - Committing the helper, and recording which slices it fetched, would make the margin reproducible.
- **ScrollGT v0.9.0 is in another repository.** The tag and the release's new row could not be checked from here.
  The draft's cite test that needs the sibling checkout skips.

## Verification

- **Tests:** the 512³, CT-context, tracing-context, chain-guard, filing, form-answer, raw-reader, ledger and
  suite-guard tests give 194 passed and 5 skipped on main.
- **The new test:**
  - it passes;
  - each of three edits to the data behind it fails it: a padded row under our tracer's, connected components above
    a padded row, and the generator above a cube-only row.
- **Ruff** 0.9.10 `check` and `format` are clean on the test file.
- **No independent review this round.** The change is one computed binding, checked by perturbation.
