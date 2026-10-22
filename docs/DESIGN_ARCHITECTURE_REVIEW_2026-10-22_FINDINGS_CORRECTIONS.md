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

Main has not moved since #189. There are no open pull requests. This round covers the 17:12 UTC firing.

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
  - **The ledger gains the claim**, with a new rule: an entry may name the correction a paragraph must carry
    (0.25 vx, "same surface", nearest-neighbour or re-parametrisation), and then no other withdrawal word clears
    it.
  - Six dated paragraphs assert the claim, in five reports and the villa flatten draft. Each now carries a dated
    note. The preregistrations are frozen records and are unchanged.
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
  - Its `config.json` records the prize gates without enforcing them, and `skel_dist` is never gated since Phase
    4b.
  - **Change:** FINDINGS' deliverables list describes the rule, with a dated note.
- **"Cross-scroll generalization remains unmeasured".**
  - This is a July bullet about an experiment invalidated by an axis-order bug. The first valid cross-scroll
    measurement (lift 1.29) came after it.
  - **Change:** the bullet points to it.
- **Tests:**
  - `tests/test_findings_headline_numbers.py` is new, with 9 tests. Each recomputes a figure from its JSON or
    report table and asserts FINDINGS states it, rounded once. They cover:
    - the detector table, the epoch-selection caveat against the sweep, and the SOTA row;
    - the anchor and current-code nulls with their control sensitivity;
    - the flatten and fit-only floors;
    - each row of the four-case table;
    - each null's corrected bound;
    - the 67.6%;
    - the promotion rule against `train.py` and `config.json`.
  - `tests/test_withdrawn_claims_stay_withdrawn.py` gains the 7.15 vx claim, the named-correction rule, and a test
    of the rule.

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
  filing records. The filing records disclose its withdrawal. No ledger entry was added, because each would need
  an annotation; FINDINGS and the summary are correct.
- **The summary's finding 45** carries the 09-27 correction in its header. Its body still says the anchor control
  "was fitted on a different villa tree".
- **`the_writer_effect_is_real_and_my_prediction_missed.md`** scales the inner flatten pair's "2.65 %/vx". That
  sensitivity divides by a nearest-neighbour distance, the kind the 09-22 correction calls void. The report
  records that its prediction missed.
- **Corrections propagate by hand.** Each one this round fixes was made in a new report, and missed FINDINGS.
  The ledger is the only mechanism that carries a correction to other documents, and only for claims entered in
  it.

## Verification

- `pytest tests/test_findings_headline_numbers.py tests/test_withdrawn_claims_stay_withdrawn.py`: 9 and 15
  passed.
- **Mutants**, in a scratch worktree, each restored after it ran. 25 of 26 fail a test. The one that does not
  is a phrase wrapped across lines, which the mutant script could not match. The test reads that phrase on
  single-spaced text, and binds it. The 25 are:
  - 18 figures in FINDINGS;
  - the 7.15 vx sentence restored;
  - the 09-27 note dropped;
  - the summary's bound;
  - one report's note removed;
  - three JSON values;
  - a sweep cell.
- **Guards and audit:**
  - The nine doc-guard files and six report-number files were run on main and on the branch, with the doc
    audit (`audit_doc_references.audit()`). They differ only by the 11 new tests: 186 passed on main, 197 on the
    branch.
  - The one failure is `test_live_documents_stay_clean`, from villa paths, as on main.
  - The audit gains no entries.
- Ruff 0.9.10 `check` and `format` are clean on both test files.
- **Pending:** the probe re-run on the branch, the standard suite, and the independent review.
