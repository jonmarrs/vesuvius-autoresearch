# Design and architecture review — the owner's #212, finding 97

Date: 2026-10-24. Baseline: `4cf3750c` (main after the owner's #212).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 10:12, 11:12 and 12:12 UTC firings. #212 widens #209's registered CT-context test to the five
Scroll-1 256³ cubes (amendment 1, `cb9bd1ab`) and reports its result, finding 97
(`reports/neural_tracer_ct_context.md`). With 128 voxels of real CT around each 256³ cube, villa's neural tracer
keeps its seeds, and its coverage rises 1.76–2.78× on all ten. Every registered prediction held on both sets.

## What changed

- **Finding 97's JSON is now bound to the findings it compares with.**
  - The owner's test binds every figure in the report to `reports/neural_tracer_ct_context.json`.
  - That JSON carries its own copies of the "before" rows: finding 91's, finding 94's, finding 96's records, and
    our tracer's published rows. Nothing checked the copies against the committed findings.
  - `tests/test_neural_tracer_ct_context_report.py` now does, for all ten cubes.
- **The stored verdicts are now the registered rule's.**
  - The JSON stores each set's status, the predictions and the reading.
  - The new test recomputes them with the script's `outcome()` from the JSON's own rows and records. That covers the
    registered Scroll-5 five and amendment 1's Scroll-1 five, judged apart.
  - It also checks each record's dropped share against its counts.
- **Finding 96's open question now points to its answer.** Finding 96 said how much of the gap the window rule
  explains was untested, pending this run. A dated note in `reports/neural_tracer_boundary.md` now cites finding 97
  and its 1.76–2.78× coverage rise. The figure is bound to the JSON.

## Verified, no change needed

- **The run's identity.** The JSON records:
  - every padded CT's and presence's core identical to findings 85 and 91;
  - the smoke reproducing finding 91 point for point;
  - all ten runs present;
  - the same seed dots as finding 91 on every cube.
- **The manipulation took.** The closest seed is 0 voxels from a face on eight cubes, and 1 and 2 on the held-out
  two, where finding 91 had 19 on all.
- **Amendment 1 came first.** It was committed at 20:29 PDT on 2026-10-23, before the runs the report times from
  21:02.
- **#212's code is the code reviewed in round 114's trial merge.** It adds the raw-slice reader, the Scroll-1 set
  and per-set verdicts. The guard from #217 survived its chain edit.
- **The owner's open PRs follow up on finding 97:**
  - #221 folds it into the October filing draft;
  - #219 withdraws #206's octant registration;
  - #220 pre-registers the 512³ cubes, and its new chain already uses #217's guard.

  None of them touches the two files this round edits.

## Verification

- **Tests:**
  - the report and boundary tests give 18 passed and 1 skipped;
  - with the other CT-context, raw-reader, guard, tracing-context, ledger and suite-guard tests, 135 passed and
    1 skipped before this round's additions.
- **Perturbations:** each of 12 fails a test:
  - one edit to each of the five copied sources;
  - three stored verdict fields;
  - a record's count;
  - a padded coverage;
  - two edits to the pointer's text.
- **Ruff** 0.9.10 `check` and `format` are clean on the test.
- **No independent review this round.** The changes are three tests and a dated note, each checked by
  perturbation.
