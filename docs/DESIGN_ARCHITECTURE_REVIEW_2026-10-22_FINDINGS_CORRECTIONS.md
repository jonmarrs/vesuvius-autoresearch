# Design and architecture review — corrections that never reached FINDINGS.md

Date: 2026-10-22. Baseline: `d6ee188a` (main after #189).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `FINDINGS.md`, the document the README sends readers to for "honest results", and how corrections reach
it.
- #187 and #189 measured which numbers in the October filing draft and the README were bound to their sources.
  Both recorded that `FINDINGS.md` had not been probed.
- **How corrections are made.** A correction in this repository is a new dated report, with a dated note in the
  reports it supersedes.
- **What guards them.** `tests/test_withdrawn_claims_stay_withdrawn.py` keeps a ledger of withdrawn claims. It
  fails if any document asserts one in a paragraph that does not also say it was withdrawn.
- **What isn't guarded.** A correction that never enters the ledger has no guard.

Main has not moved since #189. There are no open pull requests. This round covers the 17:12 to 21:13 UTC firings.

## Method

- **The probe.** Each number in `FINDINGS.md` was changed by one in its last digit, and the five test files that
  read the document were run, in four scratch worktrees. This is #187's probe.
  - **560 numbers were tried, and 5 were bound** on main. These were the gap-fix row bound in #189 and the
    ~12% beside it.
- **By hand.** The spiral-fitting section, the current-results section and the deliverables list were read against
  their reports, and every data figure was traced to its JSON or report table.

## What changed

- **The flatten "lands on surfaces 7.15 vx apart".**
  - `the_flatten_moves_the_grid_not_the_surface.md` (2026-09-22) found the two stock flattens lie on the same
    surface, 0.25 vx apart along the normal. The 7.15 vx is a nearest-neighbour distance between two samplings
    of it on a 20 vx grid.
  - That report says "several later documents" carry the claim. It was never added to the ledger.
  - `FINDINGS.md` still said "land on surfaces **7.15 vx apart**". The paragraph passed the ledger's test only
    because it said "superseded" about an unrelated figure.
  - **Change:** FINDINGS says the flatten lays the same surface out on grids ~7 vx apart in-plane, 0.25 vx along
    the normal.
  - **The ledger gains the claim**, with two new rules.
    - An entry may name the correction a paragraph must carry: 0.25 vx (0.23–0.26), "same surface" or
      re-parametrisation. Then no other withdrawal word clears it. "Nearest-neighbour" does not, since the
      uncorrected report used that word itself.
    - A dated document corrected at its head, before its first section, is cleared as a whole. The corrected
      original report is cleared this way.
  - The pattern takes any 7.x figure, up to three intervening words, table cells, and the reversed order
    ("6.6–7.3 vx from *both* stock surfaces").
  - **What it found, and the change for each:**
    - four dated reports: a dated note beside the claim;
    - the radial-study report and the villa flatten draft: a note at their head. The draft's earlier note had
      sat inside the posted PR text;
    - the summary's finding 52: corrected in place.
  - The preregistrations are frozen records and are unchanged.
- **The anchor study's control was "fitted" on another tree.**
  - FINDINGS' 09-21 correction said the anchor ablation's control `curbase_s1-s3` was fitted before a villa
    submodule bump and its arms after.
  - On 09-27, `the_anchor_control_was_cross_tree.md` and `control_sensitivity.md` found that every current-tier
    fit ran from one `d8c5f488a` copy. The split is at the render, and was measured inert (+1.44%, inside the
    3.04% render noise).
  - So the −0.86% → −5.49% move is sensitivity to which seeds serve as control, not a bias removed.
  - **Change:** FINDINGS carries the 09-27 correction.
- **The current-code null's ±3% bound was withdrawn.**
  - FINDINGS quoted the same-winding (current) null as +0.28%, 95% CI [−2.56%, +3.13%].
  - On 09-27, `control_sensitivity.md` showed that interval rests on three control seeds at CV 0.0124. Against
    the six render-matched seeds it is −4.41% [−12.18%, +3.37%]. The summary's finding 45 says its "±3%" is
    withdrawn.
  - **Change:** the same note in FINDINGS gives the render-matched interval and withdraws the bound.
- **The same-winding (pinned) null was bounded at the registered 8.3%.**
  - FINDINGS and the summary's finding 22 said the ink was unchanged "within ~8.3%". That MDE used the df=3 CV
    0.0421, which `noise_floor_by_tier.md` superseded on 2026-09-12.
  - With the pinned tier's 0.0514 at 3 v 6, it is 10.2% (`manipulation_effects_survey.json`). The patch-study
    nulls beside it already carry the same correction (~10% → ~12%).
  - **Change:** both say ~10%, and name the registered 8.3%.
- **"Two pre-registered cases … in opposite directions", above a four-row table.**
  - **Change:** it now reads four cases, in three directions, as the summary's finding 23 has it.
- **The loop "promotes only topology-improving configurations".**
  - It promotes on `val_f1` against the incumbent: more than `F1_NOISE_TOLERANCE`, with an AP-prevalence lift
    above 1.02 (`scripts/training/train.py`).
  - Its `config.json` records the prize gates without enforcing them (the dataclass default enforces them), and
    `skel_dist` has not been gated since Phase 4b.
  - **Change:** FINDINGS' deliverables list describes the rule, with a dated note.
- **"Cross-scroll generalization remains unmeasured".**
  - This is a July bullet about an experiment invalidated by an axis-order bug. The first valid cross-scroll
    measurement (lift 1.29) came after it.
  - **Change:** the bullet points to it.
- **Four more, found by the independent review:**
  - **The tracer.** FINDINGS said our tracer "loses to connected components" and that the rankings "require
    recomputation". The pre-registered rescore of 2026-10-09 did that recomputation, with ScrollGT's own
    scorer (`tracer_rescore.json`).
    - Raw ERL trails connected components on all 11 cubes, by 3.9–6.2×.
    - Merge-penalized ERL leads on 4 of 11, all three 512³ cubes among them.
    - **Change:** FINDINGS gives the rescore.
  - **The PHerc 1667 columns.** FINDINGS gave the partial-extent extremes, 0.667 and 0.0 at n = 3v2. The
    full-band rows superseded them: arm C 0.575 and legacy 0.595 at n = 18v17, against a noise floor of 0.578.
    **Change:** FINDINGS gives the full-band rows.
  - **The 64 px verdict.** "Detection at 64 px is window-limited" contradicts FINDINGS' own Phase 5, where a
    64 px-lateral recipe reads ink at held-out AUC 0.709. **Change:** it is struck through and marked
    superseded, as its sibling TimeSformer bullet already was.
  - **"Agree on `total_fg_pixels` to 1.2%".** That is the CV of the three registered seeds, which
    `control_sensitivity.json` shows are unusually tight; across all nine it is 6.4%. **Change:** FINDINGS says
    so.
- **Smaller fixes:**
  - FINDINGS' "selects and reports at the topology-optimal point" now names the reporting threshold.
  - Dated notes on `samewinding_verdict.md`'s 8.3%, `decoupling_does_not_cleanly_reproduce.md`'s ±3%, and the
    writer-effect report's two flatten %/vx rows. Those rows divide by nearest-neighbour distances.
- **Tests:**
  - `tests/test_findings_headline_numbers.py` is new, with 12 tests, and is in the standard suite. It reads
    `train.py`'s promotion constants, which makes it a test of the loop's code. Each recomputes a figure from its JSON or
    report table and asserts FINDINGS states it, rounded once. They cover:
    - the detector table, the epoch-selection caveat against the sweep, and the SOTA row;
    - the anchor and current-code nulls with their control sensitivity;
    - the flatten and fit-only floors;
    - each row of the four-case table;
    - each null's corrected bound;
    - the 67.6%;
    - the promotion rule against `train.py` and `config.json`;
    - the tracer counts against `tracer_rescore.json`;
    - the full-band column rows;
    - the superseded 64 px verdict;
    - the re-render's +1.44%;
    - the 1.2% and 6.4% CVs.
  - `tests/test_withdrawn_claims_stay_withdrawn.py` gains the 7.15 vx claim, the named-correction and head
    rules, and a test of the rules with nine live phrasings.

## Verified by hand, no change needed

- **Current results:**
  - the detector table (`cross_scroll_measurement.json`; the cross-scroll AP is 0.14448, so 0.144);
  - epoch 7 of 12 at 0.7001 against the last epoch's 0.6982;
  - the SOTA row, 0.662 / 0.742 / 3.24 / 0.865, with the baseline at lift 0.98.
- **Spiral section:**
  - the anchor ablation, −0.86%, p=0.76, [−10.21%, +8.50%];
  - 3.4× noisier (0.0419 against 0.0124);
  - +1.39%, p=0.0032;
  - +1.18% on current code;
  - +1.32%, p=0.0013 tree-matched;
  - the fit-only CV, 0.0909 [0.0568, 0.2230], F(5,5) p=0.67;
  - 3.04%, 9.5×;
  - the four-case table's p-values, from both verdict JSONs and the same-winding report;
  - 12.59% for the duplicated winding;
  - the radius gradient, 0.9421 → 0.7198, r = −0.21 over 35,963 patches.
- **"Window-compliant … held-out AUC 0.70–0.71".** This spans epoch 7's 0.7001 under the Gaussian blend and its
  0.7090 under the uniform one.

## Observations for the owner (not changed)

- **The ledger's exemption is coarse.** Any withdrawal word in a paragraph clears every claim in it. That is how
  the 7.15 vx claim survived in FINDINGS. Only the new entry names its correction. The older entries could each
  name theirs too.
- **The ±3% interval** is still quoted, in its own dated context, by about a dozen reports and both September
  filing records. The filing records disclose its withdrawal, and `decoupling_does_not_cleanly_reproduce.md` now
  carries a note. No ledger entry was added: most copies would need an annotation or a head note. FINDINGS and
  the summary are correct.
- **The summary's finding 45** carries the 09-27 correction in its header. Its body still says the anchor control
  "was fitted on a different villa tree".
- **The prize gates' two defaults.** `config.json` sets `enforce_prize_gates: false`, while `ExperimentConfig`
  defaults to true and the loop falls back to defaults without a config. FINDINGS describes the loop's
  `config.json`.
- **Prose in the case table.** The guard column ("passes a real ink regression") and "in three different
  directions" are wording, not figures, and no test binds them.
- **Corrections propagate by hand.** Each one this round fixes was made in a new report, and missed FINDINGS.
  The ledger is the only mechanism that carries a correction to other documents, and only for claims entered in
  it.

## Verification

- `pytest tests/test_findings_headline_numbers.py tests/test_withdrawn_claims_stay_withdrawn.py`: 12 and 15
  passed.
- **The probe, re-run on the first commit** with the new test: 70 of 572 numbers are bound, against 5 of 560 on
  main. The second commit binds the tracer counts, the column rows and the CVs as well.
- **Mutants of the first commit**, in a scratch worktree, each restored after it ran. 25 of 26 fail a test. The
  one that does not is a phrase wrapped across lines, which the mutant script could not match. The test reads
  that phrase on single-spaced text, and binds it. The 25 are:
  - 18 figures in FINDINGS;
  - the 7.15 vx sentence restored;
  - the 09-27 note dropped;
  - the summary's bound;
  - one report's note removed;
  - three JSON values;
  - a sweep cell.
- **The review's 52 mutants**, re-run on the final commit: 45 fail a test. The seven that pass are:
  - two rewraps, which the test is meant to pass;
  - the two prose edits above;
  - three edits to promotion logic that FINDINGS does not state:
    - removing the gate check;
    - changing the return;
    - flipping the dataclass default.

  The review reports that `test_autoresearch_measurement.py` catches a broken `promotion_decision`.
- **Guards and audit:**
  - The nine doc-guard files and six report-number files were run on main and on the branch, with the doc
    audit (`audit_doc_references.audit()`). They differ only by the 14 new tests: 186 passed on main, 200 on the
    branch.
  - The one failure is `test_live_documents_stay_clean`, from villa paths, as on main.
  - The audit gains no entries.
- Ruff 0.9.10 `check` and `format` are clean on both test files.
- **The standard suite** with the locked-package overlay.
  - The first run gave one new failure: `test_validation_suite_covers_the_loop.py`. The new FINDINGS test reads
    `scripts/training/train.py` by path, so it is a test of the loop's code.
  - It is now listed in `scripts/run_validation_tests.py`, which brings the suite to 126 files.
  - Re-run: 2811 passed, 22 skipped and 1 xfailed. That is main's 2799 plus the 12 new tests, with main's ten
    environmental failures: nine missing villa files, plus gp_winner.
  - Of the other files, only `test_prize_promotion_gates.py` reads a changed document (FINDINGS).
- **Independent review** of the first commit, in a worktree without villa. It found nothing blocking.
  - **It confirmed:**
    - every correction against its source: the normal offset 0.2534, the control-sensitivity rows, the +1.44%
      re-render, and the pinned bound 2.80 × 0.0514 × √(1/3 + 1/6) = 10.2%;
    - the promotion wording against the code.
  - **Its should-fix findings:**
    - the four stale claims above;
    - the ledger pattern missing live copies (the radial-study report, finding 52, reversed and table forms);
    - "nearest-neighbour" clearing a stale paragraph;
    - mutants that passed (the +1.44%, the gap-fix row, the `enforce_prize_gates` text).

    All are fixed in the second commit.
  - **Its nits:** all addressed except the prose in the case table, which is left as an observation:
    - citations;
    - the in-place rewrite;
    - the note inside the posted PR text;
    - the docstring;
    - the rounded-CV ratio;
    - "has not been gated".
