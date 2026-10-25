# Design and architecture review — the owner's #232 (finding 100) and #231

Date: 2026-10-25. Baseline: `4f359172` (main after the owner's #232); #231 merged at `11b29881` during the round.
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 15:13 UTC firing. The 08:12–14:12 firings found main unmoved after #230. #231 folds finding 99
into the October filing draft. #232 registers and reports finding 100 (`reports/neural_tracer_steep_heading.md`).
- It traces the seed dots villa's neural tracer skips where its CT axis lies more than 35° from the presence
  direction, in two arms: `sheet` (the presence direction projected into the CT's sheet) and `keep` (villa's own axis).
- Sheet's coverage rose 1.20× and 1.43× on the two held-out Scroll-5 cubes, and 1.003–1.024× on Scroll 3.
- P1, P3, P4 and P5 held. P2, a median of at least 1.05× on Scroll 3, failed.

## What changed

- **The JSON's copied rows are now bound to their sources.**
  - `reports/neural_tracer_steep_heading.json` carries its own copies of the baseline: findings 97 and 98's rows at
    both tolerances and their run records. It also copies our tracer's published rows.
  - The verdict, the manipulation check and the ranking are computed from those copies, and nothing checked them
    against the committed findings. Round 116 found and closed the same gap in finding 97.
  - They are equal today. `tests/test_neural_tracer_steep_heading_report.py` now checks:
    - all 21 cubes' copies against `reports/neural_tracer_ct_context.json` and
      `reports/neural_tracer_ct_context_512.json`;
    - our tracer's rows against `reports/neural_tracer_entrant.json` and `reports/tolerance4_rescore.json`.
- **Finding 99's open question now points to its answer.**
  - Finding 99 said that what a heading following the sheet would add, in traces and coverage, was untested, and
    that it needed a GPU run.
  - A dated note in `reports/neural_tracer_heading_residual.md` now cites finding 100's coverage factors on both
    held-out sets.
  - The new test binds the note's figures to finding 100's JSON.

## Verified, no change needed

- **The registration came first.**
  - `9d31f36d` was committed at 00:37:52 PDT. The chain started at 01:09:57 from that commit, and its log records it.
  - Since the registration, the scripts are unchanged. The chain's only change is the renamed refusal prefix, which
    the report discloses. None of its refusals appear in the log.
- **The decision logic is the registration's.** Recomputed independently from the JSON:
  - P1: 1.196 and 1.425;
  - P2: rises on 8 of 8, but the median is 1.017;
  - P3: 10 of 10;
  - P4: 9 of 10, the exception being `s3_04494_00994_01494_512`;
  - P5: 0.995–1.015;
  - the manipulation check holds for both arms.

  The reading is the table's row for "only P1", with P3 and P4's clauses. The owner's test also recomputes it with the
  script's `verdict`.
- **The arms are villa's code with one change.** Read against villa at the pinned ccb431818:
  - villa calls `seed_headings` by its module-global name, and reads the seed-heading policy from the same module when
    it writes `run.json`. So the launcher's replacements reach both, and a resume with another arm is refused.
  - The launcher's agree test, sign and chunking are villa's. `ct_seed_heading` is `sheet_heading` of `ct_normal`, as
    the launcher calls them.
  - The sheet arm's "more than 45° out of the sheet" is a projection shorter than cos 45°.
  - villa's training seeds (`oriented_seed_heading`, from `directed_seed`) take the CT axis signed along the tangent,
    with no 35° test, as the registration says.
- **The run's logs match the report.** All timings come from the committed logs, and the 42 `DONE` lines are in the
  registered order. The smoke gates the arms in the chain.
- **The registration's commit message says 24 tests.** At `9d31f36d`, pytest collects 23, as the report says.
- **Ruff** 0.9.10 is clean on #232's two scripts and two test files.
- **#231's figures are finding 99's**, and its test computes each from the JSONs:
  - the 0.266, 0.353 and 0.011–0.088 drop shares;
  - the 10–16° and 58–81° angles and the 52–74° tilts on the ten held-out cubes;
  - r 0.98 and Spearman 0.92;
  - E2's 0.12 of 1,347 dots, failing on 18 of the 21 cubes;
  - E3's 0.127 and 0.169.

  The draft keeps finding 99's failed expectations out of the registered tally, since finding 99 was not
  pre-registered, and states them apart.

## Observations for the owner (not changed)

- **The draft's finding 99 text predates finding 100.** It says "nothing was traced again", and among the claims it
  does not make lists "following the sheet would add coverage". Finding 100, merged before #231, has since traced
  those dots, and sheet's coverage rose 1.20× and 1.43× on the two held-out Scroll-5 cubes. Both sentences remain true
  of finding 99 alone. The owner's open #233 folds finding 100 into the draft, so the draft is not changed here.

- **`score` treats a missing smoke result as passing.**
  - `status` returns `SMOKE_FAILED` only when `smoke.json` says the smoke failed. With no `smoke.json` it can return
    `OK`. Round 114 recorded the same pattern in #209's script.
  - Here the chain writes `smoke.json` before any arm runs, and the committed JSON records the smoke as identical. The
    owner's test asserts that.
  - Changing the registered script now would also make the chain's freeze check refuse a resume in the same work
    directory, so it is left as is.
- **The CPU pre-flight's result is not in the repository.** The report's "all 910 dots" is finding 99's dot count for
  that cube, and the test binds it there. The pre-flight's own output, which agreed with villa on every dot, is not
  committed.
- **The classification and the runs cannot be repeated here.** They need findings 97 and 98's padded inputs, the
  checkpoint and the GPU on the owner's machine.

## Verification

- **Tests:** #232's two test files and the chain guard give 58 passed. With this round's additions, the steep-heading
  and heading-residual report tests give 20 passed and 1 skipped; the skip is the ScrollGT hashes.
- **Perturbations:** each of seven edits fails a test:
  - a finding 97 coverage, a finding 98 precision and a finding 98 record count;
  - our tracer's row in each of its two sources;
  - two figures in the note.
- **Ruff** 0.9.10 `check` and `format` are clean on the test file.
- **Doc guards, the withdrawn-claims ledger, the suite and chain guards, the filing and form-answer tests, and
  finding 96–100's tests:** 629 passed and 9 skipped.
  - The one failure is `test_live_documents_stay_clean`, which lists villa paths absent from this container's villa
    checkout.
  - Its list is the same as in round 118.
- **After merging #231:** the filing, form-answer, ledger and both report tests give 107 passed and 5 skipped, for
  sibling checkouts absent here. Ruff 0.9.10 is clean on #231's test file.
- **Doc audit:** #232 adds no entries, and neither does this branch.
- **No independent review this round.** The change is a dated note and two tests, each checked by perturbation.
