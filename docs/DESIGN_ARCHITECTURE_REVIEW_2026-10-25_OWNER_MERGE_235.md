# Design and architecture review — the owner's #235 (villa draft: volume tracing stops the 35° seed skip)

Date: 2026-10-25. Baseline: `ac43650f` (main after the owner's #235).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 22:12 UTC firing. The 21:12 firing found main unmoved after #237. #235 adds a villa PR draft,
not posted, in `docs/VILLA_DRAFT_volume_seed_heading.md`:
- **The patch** (`repro/fibers/villa_volume_seed_heading.patch`) deletes the 35° skip from villa's `_seed_heading`.
- **The measurement** is finding 100's `keep` arm.
- **A GPU re-run on villa's main** shows the two held-out Scroll-5 cubes trace identically there, with and without the
  patch.

## What changed

- **The draft miscounted the patch.**
  - It summarised the patch as "+23/−4: two lines removed from `_seed_heading`, one docstring line, a new 21-line
    test".
  - The patch rewords two docstring lines (−2/+2). Its 23 added lines are the 21-line test and those two.
  - The draft now says "two docstring lines reworded". `tests/test_villa_draft_volume_seed_heading.py` counts each
    part from the patch and binds the sentence.
  - The patch itself is unchanged, so the re-run's frozen copy still matches it.

## Verified, no change needed

- **The patch is finding 100's `keep` arm.** The owner's test checks it on 2,000 random cases. It runs villa's own
  `_seed_heading`, from source, with and without the patch's two lines, and compares it with the launcher's `choose`
  for `villa` and `keep`.
- **The patch:**
  - it applies to the pinned villa (`git apply --check`);
  - it removes only the skip and the docstring clause;
  - its new test fails 5 of 9 cases without the change, by the angle arithmetic: 36°, 60°, 89°, 91° and 120° lie more
    than 35° off, and 179° does not.
- **The draft's claims about villa hold at the pin:**
  - training's seeds (`data/seeds.py`, `data/targets.py`) use `oriented_seed_heading`, which signs the CT axis along
    the direction with no 35° test, and its docstring says "exactly as in inference and collection";
  - the VC3D service signs the CT heading along the request's direction, and falls back to that direction when there
    is none;
  - `tracing/inference.py` traces both ways;
  - neither has the skip.
- **The draft's figures are finding 100's**, and the owner's test computes each from its JSON:
  - the table;
  - the example's 316 of 895, 288 traced, and 507 traced (251 of them dots that fail the test);
  - the summary's factors and precision ranges;
  - the figure's 0.091 and 0.016 length shares, whose covered shares reproduce the scorer's coverage.
- **The re-run:**
  - the chain (`repro/fibers/run_villa_seed_heading_rerun.sh`) was committed at 13:13 PDT, before its 13:16–13:21
    run;
  - it uses the repository's loop guard;
  - `reports/evidence/villa_volume_seed_heading_rerun.json` records all four runs identical to their sources point
    for point, with equal seed counts and the control, before against after, differing;
  - the chain and wrapper logs match.
- **The body follows villa's pull request template.** It leaves the motivation to the owner and the
  personal-verification box unticked, as villa's CONTRIBUTING requires for LLM-assisted PRs.

## Observations for the owner (not changed)

- **One doc-audit entry.** The draft cites villa's main as 322cb0899 in backticks. This repository's villa checkout
  is at the pin, so the audit cannot resolve it.
  - The live-documents test checks paths only, so nothing fails.
  - The owner's test binds the backticked form.
- **Not checkable here:** villa's open PRs, #2165 and #2265, and villa's main at 322cb0899. They are outside this
  session's repository scope.

## Verification

- **Tests:** #235's test file, the chain guard and the suite guard give 45 passed before this change. The draft test
  gives 9 passed after it.
- **Perturbation:** restoring "one docstring line" fails the draft test.
- **Ruff** 0.9.10 `check` and `format` are clean on the test file.
- **Doc guards, the withdrawn-claims ledger, the suite and chain guards, and the filing, form-answer, draft and
  finding 100 report tests:** 541 passed and 6 skipped.
  - The one failure is `test_live_documents_stay_clean`, which lists villa paths absent from this container's villa
    checkout.
  - Its list is the same on main.
- **Doc audit:** #235 adds the one entry above, and this branch none.
- **No independent review this round.** The change is one phrase and its binding.
