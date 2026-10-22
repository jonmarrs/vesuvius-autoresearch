# Design and architecture review — the supervised re-analysis and where its numbers are quoted

Date: 2026-10-22. Baseline: `995ab150` (main after #185).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: finding 77, the re-analysis of findings 71–76 on villa's supervised region, and the documents that quote
those findings.
- **The analysis.** `scripts/reanalyse_supervised.py` and its preregistration
  (`docs/preregistration/2026-10-04_supervised_reanalysis.md`). Also each original finding's registered rule
  (`docs/preregistration/2026-10-03_*`, `2026-10-04_install_route_band_vs_labels.md`,
  `2026-10-04_objective_vs_labels.md`) and its script.
- **The record.** `reports/supervised_reanalysis.{md,json}` and the post hoc `posthoc_q1_supervised_tiles`.
- **The quotations.** `reports/SPIRAL_FINDINGS_SUMMARY.md`, the six original reports, the October filing draft and
  `docs/VILLA_DRAFT_1818_smooth_measurements.md`.

No earlier review covered these. The re-analysis corrected five reports and is cited in the filing draft, and its
script has no test. Main has not moved since #185. There are no open pull requests. This round covers the 08:12
UTC firing.

## What changed

- **The filing draft quoted finding 72's whole-surface figure as its faithfulness claim.**
  - The draft's main text said the scorer's agreement with villa's labels "does not change (|ΔAP| < 0.001 in all
    8, none resolved)". That is finding 72 on the whole surface, which counted unannotated ink as negatives.
  - The correction registered that the draft would quote supervised-region numbers. Where the labels are defined
    it is |ΔAP| < 0.01 in all 8 (the registered test), < 0.001 in 6, and 1 of 8 resolved: `20231031143852`,
    ΔAP −0.0064, toward linear.
  - The band and coarse-grid figures beside it were already the supervised ones. A test pinned the old string.
  - **Change:** the draft gives the supervised figure, and its test reads it from `supervised_reanalysis.json`.
    The test now also refuses the old string.
- **The draft's failed-prediction list gives findings 71–76 as registered, on the whole surface, and did not say
  where the correction changes them.**
  - Where the labels are defined, three of the 22 change:
    - **Finding 71 prediction 1 holds.** The prediction is |ΔAP| < 0.02 in ≥ 6 of 8. It failed only on three gate
      exclusions; all 8 pass inkagree's gate there.
    - **Finding 74 prediction 3 holds.** Step 1.0 against 0.5 is 4 of 8 resolved, below the k = 6 rule. The list
      said "7 of 8" a few lines after the correction said "not consistent".
    - **Finding 76 prediction 1 is undetermined.** No window qualifies.
  - **Change:** each of the three items says so. The count stays 22, because each failed as registered. Whether
    to count them is the owner's call.
- **The spiral summary marked only finding 74.**
  - The correction's reporting plan: "Old numbers stay, marked as computed on the unsupervised domain", in each
    report, the summary and the draft. The six reports each carry a correction note at their head.
  - In the summary, only finding 74's entry had a marker. Entries 71, 72, 73, 75 and 76 gave the whole-surface
    numbers unmarked, so a reader of entry 75 alone saw "+8%" and "+10%". Finding 77, below them, gives the
    corrections.
  - **Change:** each of the five entries now has a marker in 74's form, with its supervised result.
- **Two descriptive claims do not hold where the labels are defined, and their reports' notes did not say so.**
  - **Finding 71.** Its report's post hoc sensitivity says smooth is "a hair worse in every segment (6 of 8
    resolved)". Where the labels are defined the sign reverses: ΔAP > 0 in 7 of 8, 1 resolved toward smooth. The
    registered verdict, no consistent difference, survives on both.
  - **Finding 72.** "< 0.001 in all 8, none resolved" becomes < 0.001 in 6 of 8, 1 resolved. Its registered P2
    survives.
  - **Change:** both reports' correction notes now say so. The summary's markers for 71 and 72 say the same.
- **The villa #1818 draft predates the correction.**
  - The draft is unposted, and posting needs the owner's approval. It was written 2026-10-03, the day before the
    correction, and quoted whole-surface label numbers:
    - "|ΔAP| ≤ 0.0001" on fine meshes; where the labels are defined the largest is 0.00012;
    - "resolved in 6 of 8, about +1–2%" on coarse meshes; where the labels are defined it is 8 of 8, median +0.84%.
  - It also said its numbers were "test-bound via the October draft". The October draft quotes the supervised
    coarse figure, so those two numbers were bound to nothing.
  - **Change:** the text quotes the supervised numbers, and says where it scored. A dated status line records the
    update. Its notes name the source and the new test. The count figures do not involve the labels, and are
    unchanged.
- **The re-analysis report described its window rule as stricter than the one it applied.**
  - The report said the registered rule was "≥ 25% of a 2048-px window supervised". The script keeps a window when
    its supervised pixels are ≥ 25% of the window's mesh-valid pixels. That is the preregistration's wording, and
    the more lenient of the two.
  - Zero windows qualified either way. Supervision covers 4–15% of each segment's mesh-valid domain (finding 72's
    rows).
  - **Change:** the report and the post hoc script's docstring state the rule as applied, with that coverage.
- **Tests:**
  - `tests/test_supervised_reanalysis_numbers.py` is new, with 7 tests, outside the standard suite like the repo's
    other report-number tests. It checks:
    - each tally against its 8 rows;
    - that each row was scored on mesh-valid ∩ supervised, with ΔAP = AP(B) − AP(A);
    - each verdict against its finding's own registered rule;
    - every figure in the report's table;
    - the summary's markers;
    - the two reports' notes;
    - the villa draft, including its label-free count figures, from findings 72 and 73's artifacts.
  - `tests/test_filing_2026_10_numbers.py`: the finding-72 test is rebound to the supervised rows, and one test is
    added for the three list notes.
- **Mutants.** Each of these fails at least one test:
  - in the draft:
    - the old finding-72 figure restored;
    - the 74 P3 note dropped;
    - the 76 P1 note dropped;
  - in the summary:
    - the 71 marker dropped;
    - the 75 marker given the old sizes;
  - in the reports:
    - finding 72's note reverted;
    - the window rule's old wording;
  - in the villa draft, "6 of 8, +1–2%" restored;
  - in the JSON:
    - finding 74 marked as surviving;
    - finding 71's tally miscounted;
    - a Q2 ratio that dips;
    - finding 73's tally changed;
    - a row scored on the whole surface.

## Verified, no change needed

- **The re-analysis script implements its preregistration.**
  - The arms, levels and blocks are each original finding's:
    - 71: level 2, 512-px blocks;
    - 72 and 73: level 3, 256-px blocks;
    - 74: level 2, inkagree's defaults;
    - 75: level 3, inkagree's defaults.

    Each uses 2000 resamples. 71–75 use seed 20261003; finding 76's Q2 has no bootstrap.
  - The domain is mesh-valid ∩ supervised, and every stored row says so.
  - The gate is inkagree's default for every finding, as the preregistration changed it. All rows are `aligned`.
  - The bootstrap itself runs through inkagree's `compare_arms`, which is not in this container, so it is not
    re-run here.
- **Each "survives" flag is its finding's registered rule.**
  - **71:** a direction needs ≥ 6 of 8 resolved.
  - **72 P2:** |ΔAP| < 0.01 in ≥ 6.
  - **73 P2:** smooth's point estimate ≥ linear's in ≥ 6. The flag uses `b_ge_a`, as the prediction is worded. The
    resolved count is lower still.
  - **74:** k = 6 in each direction, with 0.5 as arm A.
  - **75:** 1.0 as arm A. 1.0 must be resolved better than 0.5, and 2.0 better than 1.0.
  - **76 Q2:** non-decreasing, with r = 8 > r = 0, the same expression as `analyse_objective_vs_labels.py`.
- **Every figure in the report's table matches the JSON.** The percentages are per-segment medians of ΔAP / AP(A):
  - +0.84;
  - −6.1, −1.5 (range −4.8 … +1.4) and −20.4;
  - −5.3 and +8.2.

  The ratio of the median ΔAP to the median AP does not give them (−5.4 for step 0.25). The new test pins the
  per-segment form.
- **Finding 76 Q1's zero windows are the data, not the crop.**
  - The post hoc tiles reach x ≥ 3,584–12,544 px per segment, so the arrays are not cropped below a window.
  - Each segment's supervised pixels (1.2–8.0 M) are a small share of its mesh-valid pixels (20–78 M), so no
    full-height column reaches 25%.
  - The re-analysis drops the original's other condition, that a window be ≥ 25% mesh-valid. That only removes
    windows, so it cannot change zero.
- **The six reports' correction notes** give the supervised verdicts and sizes that the JSON holds.
- **The draft's count of twenty-two** is the sum its test lists, and each item failed on the analysis it was
  registered for.
- **`docs/RESUME_AFTER_RESTART.md`** quotes the old numbers in entries dated before the correction. It is a dated
  log, so it is left as written.

## Observations for the owner (not changed)

- **The re-analysis scripts read the owner's machine.**
  - `reanalyse_supervised.py`, `posthoc_q1_supervised_tiles.py` and `analyse_objective_vs_labels.py` import
    inkagree from `/home/jon/openclaw-workspace/...` and read `spiral_out` there. None can run elsewhere, and none
    has a test of its own.
  - The new test binds what they wrote, not how they compute it.
- **Finding 71's sign is domain-dependent.**
  - On the whole surface smooth was a hair worse in all 8. Where the labels are defined it is a hair better in 7.
  - Both are ~1e-4 in AP, which supports "no consistent difference". A sentence claiming either direction would
    not.
- **Finding 72's resolved segment.** On `20231031143852` linear's scorer output agrees better (ΔAP −0.0064, CI
  [−0.0144, −0.0006]). It is within the registered 0.01, and one of 8.
- **Counting the failed predictions.** Of the 22, finding 71 P1 and 74 P3 hold where the labels are defined, and 76
  P1 is undetermined there. The list keeps them, as registered, and now says so. Counting only the predictions
  that fail on the corrected domain would give 20. That presentation is the owner's.
- **The villa #1818 draft's gates stand.** It still needs the owner's approval, a duplicate check, and a re-run of
  its numbers on the day.

## Verification

- `pytest tests/test_supervised_reanalysis_numbers.py tests/test_filing_2026_10_numbers.py`: 31 passed, 4 skipped.
  The skips are the sibling checkouts (inkdelta, inkagree, ScrollGT) not beside this repo, as on main.
- **The mutants above** were run in a scratch worktree with the change applied. Each fails one or more tests.
- **The doc guards** were run before and after the change, with the doc audit (`audit_doc_references.audit()`):
  - the guard files: the filing, headline, withdrawn-claims, quotation, decoupling, upstream-claims and
    tracking-gap tests, and the two audit test files.

  They differ only by the eight new tests: 95 passed on main, 103 on the branch. The one failure is
  `test_live_documents_stay_clean`, from villa paths, as on main, and the audit gains no entries.
- Ruff 0.9.10 `check` and `format` are clean on the changed Python files. The two existing ones were formatted
  before.
- **The standard suite** with the locked-package overlay gave 2799 passed, 22 skipped and 1 xfailed, as on main.
  - The failures are the same ten environmental ones: nine villa-file failures, plus gp_winner.
  - No suite test changed: the new test reads only reports and docs, so the suite guard does not require it.
- **The smoke test** (`scripts/smoke_test.py`) gave 9 of 11 passed and 2 skipped, as on main.
- **Independent review** of the first commit: REVIEW
