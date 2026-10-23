# Design and architecture review — the owner's #200 and #201, and pre-commit's state

Date: 2026-10-23. Baseline: `92e9f717` (main after the owner's #200 and #201).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 19:13 UTC firing.
- **#200** fixes three failures that blocked pre-commit on main:
  - a lambda mypy could not type in `tests/test_arm_tiers.py`;
  - the villa fork branch in the headless-CLI record, which read as a missing path;
  - the arm audit calling upfit_s1–3 phantoms. They are fit directories (`*-patch_<tag>`) whose ink
    is scored under detfit_up1–3.
- **#201** folds finding 95 (the octant crop) into the October filing draft, with a binding test.

## What changed

- **The arm audit's fit-directory rule had one unpinned half.**
  - #200 counts a tag as on disk when a `*-patch_<tag>` path exists and is a directory. Its two tests
    cover a fit directory, and a tag with neither directory.
  - Dropping the `is_dir()` check passed them, so a stray file with a fit's name would hide a real
    phantom.
  - `tests/test_audit_arm_coverage.py` gains that case, and the mutant now fails.
- **This review series had broken one file's formatting.**
  - `tests/test_withdrawn_claims_stay_withdrawn.py` was Ruff-format clean before round 107. One line
    round 107 added was too long.
  - pre-commit's `ruff-format` hook runs on each staged file, so the next commit touching the ledger
    would have been stopped. It is reformatted, with no other change.

## Verified, no change needed

- **#200:**
  - The typed `expand` function substitutes exactly as the lambda did.
  - The fork-qualified branch name is the doc guard's fix.
  - The phantom rule matches the audit's docstring, which defines a phantom as absent from disk.
- **#201:**
  - **The figures.** The octants' median tolerance-4 ratio is 1.0817, which the draft states as 1.08.
    The neural tracer leads on 19 of 24 octants, and P1 held. All three Scroll-5 256³ cubes trail at
    tolerance 4. Its test binds each.
  - **The reading** stays within finding 95's scope: scoring window, not tracing context.
- **pre-commit's whole-repository hooks pass on main here.**
  - mypy reports no issues in 764 files.
  - The doc-guard hook's nine files give 134 passed and 2 skipped. Its one failure,
    `test_live_documents_stay_clean`, needs villa paths and model checkpoints absent from this
    container; it failed the same way before.

## Observations for the owner (not changed)

- **37 files on main would be stopped by pre-commit's Ruff hooks when next staged.** That is 14 for
  `ruff` and 32 for `ruff-format`, not counting `repro/villa_preserved/`, which the hooks exclude.
  - Every one already failed in the form it was committed in. The review series' edits to three of
    them (the retry probe and two of #202's and #203's tests) kept their existing state.
  - They include files with recorded hashes. The fiber downloader and audit script are bound by the
    history-tolerant snapshot test, so reformatting them would not falsify their record. Others
    would need checking one by one.
  - A one-off `ruff check --fix` and `ruff format` across them is mechanical, but touches many owner
    files at once, so it is left for the owner to schedule.

## Verification

- Pending.
