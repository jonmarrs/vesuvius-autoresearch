# Design and architecture review — which numbers on the README's front page are bound to their sources

Date: 2026-10-22. Baseline: `c3b6ee7f` (main after #188).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the README's opening paragraph and its spiral-fitting box (lines 5–52), the first thing anyone reads.
- They quote 74 numbers from the detector and spiral reports.
- `tests/test_headline_numbers_consistent.py` says the two headline results "are quoted in six places; pin them
  to the artifacts". For the README it checks one thing: that a README quoting the geometry gains says
  "circular".
- #187 measured which numbers in the October filing draft were bound, and recorded that the summary and
  `FINDINGS.md` had not been probed. The README had not been either.

Main has not moved since #188. There are no open pull requests. This round covers the 14:17, 15:16 and 16:13 UTC
firings.

## Method: perturb each number, see whether a test notices

- Each number in the README was changed by one in its last digit, one at a time. The nine doc-guard files that
  read the README were run on each copy, in four scratch worktrees. This is #187's probe, with its refusal to run
  on a failing baseline.
- **131 numbers were tried, and one was bound:** the 15-minute shift budget, in the loop section.
- All 74 numbers in the headline section survived. Every data figure among them was then traced by hand to its
  JSON or report table.
- **Six README figures or claims were wrong.**
  - Five were found here. The independent review found the sixth, a claim about a printed interval.
  - Tracing them turned up a mistyped mean in the gap-fix report and the villa draft.
  - The review also found stale statements of the same claims in the summary, the villa draft and four reports.
  - All are listed below. The rest of the README's figures match their sources.

## What changed

- **The scorer's share of the 1.4% floor was quoted against the wrong figure.**
  - The README says the scorer the 1.42% "pipeline determinism" floor blamed contributes 0.0032%, "~950× too
    little". The summary's finding 47, `the_render_is_the_noise_floor.md` and `the_radial_study_design_is_invalid.md`
    say "950× too small to produce 1.42%".
  - 0.0032% is the spread of three re-scores of one fixed strip (`score_arms.sh`'s header: 249913 / 249905 /
    249906). 1.42% / 0.0032% is about 440; 950 is 3.04% / 0.0032%, the scorer against the render spread.
  - **Change:** all four say ~440× against 1.42%. Where the reports give it, 950× stays named against the 3.04%
    render spread, and the dated reports carry a dated note. `the_determinism_floor_rests_on_one_draw.md` and
    the villa flatten draft already used 950× against 3.04%; they are right and unchanged.
- **"892×" was twice rounded.**
  - The same-mesh pairs differ by 3,405 / 240,088 against 4 / 250,936, a ratio of 889.7. 892× is 1.4182% divided
    by 0.00159%.
  - **Change:** the summary, `the_determinism_floor_rests_on_one_draw.md` (title and text) and
    `pipeline_determinism_and_which_floor_applies.md` say 890×, the reports with a dated note.
  - This is the third twice-rounded figure in three rounds.
- **The gap-fix case put one fit count on two tests.**
  - The README, `FINDINGS.md` and the summary's two case tables give the gap-expander change as "+1.03% geometry,
    −10.35% ink, n=12".
  - The −10.35% is 6 against 6 fits (`gap_fix_mechanism.json`). The +1.03% is
    `gap_expander_fix_improves_the_fit.md`'s Welch test of the first five GAP fits against six (0.84764 against
    0.83897). The sixth GAP fit's `satisfied_area` exists only to four places, which allow +1.04% or +1.05%.
  - **Change:** the README says "(5 fits against 6)" and "(6 against 6)". The tables say "5v6 geometry, 6v6 ink".
    The villa draft's table marks 0.84764 as the first five fits' mean. `gap_fix_costs_ink_established.md` has a
    dated note where it quotes 0.84764 under a six-fit table.
- **The gap-fix baseline mean was mistyped.**
  - `gap_fix_costs_ink_established.md`'s summary block and `docs/VILLA_DRAFT_metrics_disagree.md` gave the BASE
    mean as 1,719,984.
  - The six BASE rows in the same report average 1,719,650.5, which is the mean `gap_fix_mechanism.json` and
    `samewinding_verdict.json` record. It is also the mean the block's own −10.35% is computed from;
    1,719,984 would give −10.37%. The analysis script prints means as `.4g`, so the block was transcribed by hand.
  - **Change:** both say 1,719,651, the report with a dated note.
- **The README's ink-null bound was the superseded one.**
  - It said both ink nulls "are bounded at ~10%". That is the registered MDE of 9.6%, from a df=3 CV.
  - On 2026-09-12 it was corrected to ~12% with the pinned tier's floor. `manipulation_effects_survey.json` gives
    11.8% for both, and `FINDINGS.md` and the summary carry the correction.
  - **Change:** the README says ~12%, and names the registered ~10%.
- **The README's seed-noise history called the current floor retracted.**
  - It said three figures (0.0125 → 0.0263 → 0.0536) "were each retracted when the next arm landed inside the
    interval".
  - 0.0536 is the current tier's floor (`noise_floor_by_tier.json`, df=11). 0.0263 was withdrawn when six
    `curbase` fits already on disk were found unused (`six_unused_seeds_double_the_current_floor.md`), not when an
    arm landed.
  - It also said the new values landed inside "the interval that had never been printed". The interval was
    printed: `noise_floor_by_tier.md` gave 0.0125's CI [0.0075, 0.0360] on the day 0.0125 was published
    (`a997c325`). It also gave 0.0263's CI [0.0169, 0.0578], and each held the next value.
  - **Change:** the README says the figure was published too low twice, and why each was withdrawn. It says that
    both times the new value sat inside the published interval.
- **The same corrections, where they recur.** The independent review found these:
  - `docs/VILLA_DRAFT_metrics_disagree.md` gave the patch-bootstrap null's power as ~10%. It is now ~12%, as in the
    README.
  - The summary's finding 13 said the gap fix raises `satisfied_area` "by 7-10 sd", with both metrics "established
    on the same twelve fits". `gap_expander_fix_improves_the_fit.md` corrected the sd figure to 4.5–5.9 on
    2026-09-03, and the geometry is on eleven fits. Both are fixed.
  - Two dated reports quoting 7 to 10 sd carry a dated note: `gap_fix_costs_ink_established.md` and
    `the_gap_fix_does_not_remove_duplicated_coverage.md`.
  - `the_determinism_floor_rests_on_one_draw.md` and `pipeline_determinism_and_which_floor_applies.md` call
    `probe_innerprob` a re-render. `the_flatten_lands_on_different_surfaces.md` found that it re-scored an
    existing strip, and the summary's finding 47 says so. Both reports carry a dated note. The 890× arithmetic
    stands; what it compares is a render pair against a re-score.
- **Tests:** `tests/test_readme_headline_numbers.py` is new, with 12 tests.
  - Each recomputes a headline figure from its JSON and asserts the README states it, rounded once:
    - the detector rows;
    - the cross-scroll distillation;
    - the ground-truth calibration (arms B and C as the clean pair);
    - both render validations;
    - the column AUCs and their n;
    - the 67.6% current-code gain, recomputed from the three baselines;
    - the flatten's offset, reproducibility cost, floor and displacement;
    - the fit-only CV, with its F-test p recomputed from the twelve counts;
    - the null bound;
    - the current noise floor.
  - Where no JSON holds a figure, it reads the report table and checks the table:
    - the same-winding geometry endpoint, checked against the ablated arm's four-place mean and the shared
      baseline's five-place one;
    - the gap-fix rows, whose means must equal the JSON's. The test also checks the report's summary block, every
      cell of the villa draft's table, and the case rows in `FINDINGS.md` and the summary;
    - the column noise floor;
    - the flatten throughput;
    - the seed-noise figures and their published intervals.
  - One test holds the scorer ratios to the counts they divide, in every document that states them. It also holds
    the pairs' stated ΔT to those counts.

## Verified by hand, no change needed

These match their sources:
- **Detector:**
  - `val_f1` 0.393 and lift 2.07 (`cross_scroll_measurement.json`, Fr143), and the cross-scroll lift 1.29;
  - the SOTA distillation's 0.662 / 3.24, best of 12 epochs;
  - 1.22 → 2.12 and ≈2.1 on the unseen scroll.
- **Ground-truth calibration:**
  - ROC-AUC 0.70–0.75, the canon teacher on the two segments;
  - 0.731–0.746 and lift 2.3–2.4 for arms B and C;
  - the legacy detector's 0.518;
  - the teacher's 0.753, and on F1 at 0.5 its 0.572 against 0.44–0.45.
- **Rendering:** NCC 0.78 against the registered 0.60, and Scroll 1's 0.59.
- **Columns:** 22 columns; 0.575 at n=18v17; 0.667 at n=3v2.
- **Spiral:**
  - +17.66% and +16.24%;
  - 5,413 constraints and −0.69%, p=0.0027. These are the report's; no JSON holds the geometry endpoint;
  - 67.6%;
  - ~7 vx in-plane and 0.25 vx along the normal (`flatten_normal_offset/stock_vs_stock_outer.json`);
  - 3.04%;
  - 9.5× (16.4 it/s against ~155), and ~11 minutes (637 s and 679 s);
  - 0.0014% and 24 pixels (`flat_displacement_floor.json`: 1,698,831 against 1,698,807);
  - −19.77% and −4.48%;
  - 0.09 [0.06, 0.22], F(5,5) p=0.67.
- **Left unbound:**
  - names and dates (2023, PHerc 1667, Sept 19–22, the "64 px window");
  - the "said 0.56–0.70" correction note;
  - the 4-voxel displacement, which is the study's design.

## Observations for the owner (not changed)

- **Two headline figures have no artifact.**
  - `analyse_same_winding.py` computes the geometry Welch test it prints (−0.69%, p=0.0027), but writes only the
    ink result to `samewinding_verdict.json`. The README's fourth decoupling case is bound to the report's table.
  - The test checks the table's −0.69% against its four-place means. Those give −0.70%, and allow −0.69% only at
    the edge.
  - The gap fix's six-fit geometry exists only as four-place rows.
  - Re-running the two analyses with the geometry written out would let both be bound to JSON.
- **The 1,719,984.** No file in the repository holds it, and no computation from its table or any subset of its
  rows gives it.
- **The preregistration** `docs/preregistration/2026-09-03_patch_bootstrap.md` quotes the superseded "7-10 sd".
  A registration is a frozen record, so it is unchanged.
- **The summary and `FINDINGS.md`** are still not probed. This round corrected the figures above wherever they
  appear, and bound the gap-fix rows in both.

## Verification

- `pytest tests/test_readme_headline_numbers.py`: 12 passed.
- **The probe was re-run with the new test.** 70 of 135 numbers in the README are bound, and 66 of the headline
  section's 78. That was before the null-bound binding, which adds the ~12%. The headline survivors are the names,
  dates and design figures listed above.
- **Mutants**, in a scratch worktree, each restored after it ran. All of these fail the new test:
  - main's version of each of the nine corrected documents (`README.md`, `FINDINGS.md`, the summary, the villa
    draft and five reports);
  - nine data-side mutants:
    - `render_reproducibility.json`'s ink;
    - `score_arms.sh`'s first re-score;
    - a BASE row in the gap-fix table;
    - the five-fit GAP mean;
    - the same-winding −0.69%;
    - a current-code baseline;
    - a fit-only count;
    - the column noise floor;
    - the stock flatten throughput.
- **The review's 41 mutants**, re-run after the second commit: 38 fail the test. Three don't:
  - a line break inserted mid-phrase in the README, which shows the test is rewrap-safe;
  - finding 13's "n=12", which is the ink test's count and right;
  - one that no longer applies to the JSON's current formatting.
- **Guards and audit:**
  - The nine doc-guard files and the four report-number files were run on main and on the branch, with the doc
    audit (`audit_doc_references.audit()`). They differ only by the 12 new tests: 169 passed on main, 181 on the
    branch.
  - The one failure is `test_live_documents_stay_clean`, from villa paths, as on main.
  - The audit gains no entries, and checks one more reference: the new note's pointer to `gap_fix_mechanism.json`.
- Ruff 0.9.10 `check` and `format` are clean on the new test file.
- **The standard suite** with the locked-package overlay gave 2799 passed, 22 skipped and 1 xfailed, as on main.
  - The failures are the same ten environmental ones: nine missing villa files, plus the gp_winner launcher.
  - Three of its 125 files read the README: `test_shift_budgets.py`, `test_villa_upstream_audit.py` and
    `test_villa_optimized_inference_smoke.py`. One reads `FINDINGS.md`: `test_prize_promotion_gates.py`.
  - The new test is outside the suite, like the other number-binding tests.
- **Independent review** of the first commit, in a worktree without villa.
  - **It confirmed:**
    - every corrected figure from its primary source;
    - every remaining 950× in live documents, which is against 3.04%;
    - that the first five GAP fits give +1.034% (p 3.92e-06) and all six +1.043%;
    - that no subset of rows gives 1,719,984;
    - 30 README figures the commit left alone.
  - **Its blocking finding:** the "never been printed" claim above, which the first commit kept and tested.
  - **Its should-fix findings:** the villa draft's power, finding 13, and `probe_innerprob`, all above. It also
    found mutants that survived in the villa draft's table, the gap report's block, and the `FINDINGS` and summary
    case rows; all are bound now.
  - **Its nits:** all addressed:
    - the same-winding check's width;
    - the unbound registered ~10%;
    - hardcoded noise figures;
    - unchecked pair lengths;
    - an unescaped regex;
    - two reads that rewrapping would break;
    - this doc's count of numbers.
