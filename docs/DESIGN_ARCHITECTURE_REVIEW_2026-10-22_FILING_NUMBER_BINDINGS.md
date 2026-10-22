# Design and architecture review — which numbers in the October filing draft are bound to their sources

Date: 2026-10-22. Baseline: `609a01c7` (main after #186).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `docs/PRIZE_FILING_2026-10_DRAFT.md`, the document that leaves the repository, and the tests that bind its
numbers.
- `tests/test_filing_2026_10_numbers.py` says that "every number in the October 2026 filing draft must match the
  artifact it comes from". Four other test files read the draft too:
  - `test_supervised_reanalysis_numbers.py`;
  - `test_tracer_rescore_numbers.py`;
  - `test_check_filing_upstream_claims.py`;
  - `test_headline_numbers_consistent.py`.
- Nothing measured which of the draft's numbers those tests actually bind. The last round found a
  whole-surface figure in the draft's main text that no test caught for what it was.

Main has not moved since #186. There are no open pull requests. This round covers the 12:12 UTC firing.

## Method: perturb each number, see whether a test notices

- Each number in the draft was changed by one in its last digit, one at a time. The five test files were run on
  each copy, in four scratch worktrees.
- 350 numbers were tried. The probe skipped URLs, code spans, PR and finding numbers, dates and list markers.
- 227 numbers were bound: changing one fails a test. 123 survived.
- Most survivors are not data: dates, versions, Python versions, section numbers and slice-step names. The rest,
  about 25, were checked by hand against their sources. Three were wrong.

## What changed

- **Finding 66's install-route effect was quoted in the wrong direction's units.**
  - The draft and the spiral summary say the published sampler image has "−5% to −9%" less ink than a source build.
  - Finding 66 measured the source build against the published image: +4.97% to +9.19%
    (`reports/step2_across_surfaces.json`). The draft negates those figures, but it states the reverse direction,
    so the figure is published / source − 1 per surface:
    - up1: −5.05%;
    - s4: −6.06%;
    - s5: −8.42%;
    - s6: −4.73%.

    That is −4.7% to −8.4%, so −5% to −8%.
  - `reports/install_route_band_vs_labels.md` said "+5–9% lower ink count", mixing the two.
  - **Change:** the draft and the summary say −5% to −8%, and the report says 5–8%.
  - The sampling-band report's "raised villa's ink count by 5–9%" is the measured direction, and stays.
- **Finding 79's current-code interval was rounded twice.**
  - The draft's failed-prediction list and `reports/soft_count_study.md`'s prose gave R = 0.52 [0.35, 0.91].
  - `soft_count_study.json` holds a lower bound of 0.34469. That is 0.345 to three places, but 0.34 to two.
  - **Change:** both say [0.34, 0.91]. The summary and the report's table give 0.345, which is right.
  - This is the second twice-rounded figure in two rounds. #186 found the post hoc scorer ρ (0.1447 quoted as
    +0.15).
- **The coarse-grid per-window range was rounded past its measurement.**
  - The draft's caveat said "a 6.2% median and up to ±40% per window". The measured range is −31.9% to +41.5%
    (`scorer_vs_labels_coarse.json`), which the draft's main text quotes.
  - **Change:** the caveat says −32% to +42%.
- **Tests: the draft's unbound numeric claims are now bound,** in `tests/test_filing_2026_10_numbers.py` (+3
  tests):
  - finding 66's range, computed in the direction the draft states. The test also checks it against the JSON's
    per-surface effects.
  - In the failed-prediction list:
    - finding 79's two ratios and intervals;
    - the shared-p95 re-score's 4.7%, against its registered < 2.5%;
    - finding 80's "38.56 vs 33.09" on `s5_14997`, and "ahead on 4 of 11, all three 512³ cubes among them".
  - In the caveats:
    - the coarse-grid range;
    - finding 78's "about 2% of annotated ink" (`scorer_sparsity_annotated.json`'s pooled recall, 2.1%);
    - finding 94's "at tolerance 2 trails on the other 13 cubes … at 4 it leads on three of them". The test
      recounts both from `tolerance4_rescore.json`: 0 and 3 of the 13 non-Scroll-3 cubes.
  - `tests/test_soft_count_report_numbers.py` binds the report's two-place interval to the JSON too.
- **Re-probed after the change:**
  - 249 of 351 numbers are bound, and 102 survive;
  - every claim listed above is now caught;
  - the probe now refuses to run if its baseline fails.

## Verified by hand, no change needed

These survive the probe, so no test binds them, but each matches its source:
- **Finding 80:** "on all 11 cubes", 4 of 11, and the 512³ cubes (`tracer_rescore.json`, before the new binding).
- **Cube counts:**
  - 11 in-sample, 8 Scroll-3 and 2 new Scroll-5 held-out cubes, 21 in all, from the groups in
    `tolerance4_rescore.json`;
  - "9 of 10" held out, finding 85. The ten held-out cubes are the 8 Scroll-3 and 2 new Scroll-5 ones, and the
    figure is bound in `test_afv_generator_entrant_report.py`.
- **Pitches:**
  - 9.6 µm is `neural_tracer_pitch.json`'s `to_um`;
  - 7.91 µm is the cubes' pitch, from `neural_tracer_entrant.md`;
  - 8.64 and 9.362 µm are villa's model card, outside the repository.
- **Finding 74 and 75's whole-surface counts** in the failed-prediction list (8 of 8 and 7 of 8; both 8 of 8)
  match their reports' registered results.
- **Finding 70's "< 1%"** is the prediction's own wording.
- **"3–13%" supervision coverage** is the re-analysis preregistration's 3.4–13.3%.
- **"80-voxel" and "20-voxel" cells** are finding 72's measured cell sizes.
- **Not checkable here:**
  - ScrollGT's "all 126 published rows" and "55 of 55" are counts in the ScrollGT repository, which is not in this
    container.
  - The "±3-voxel projection" is the 3D ink model's config.

## Observations for the owner (not changed)

- **Two twice-rounded figures in two rounds.** Both were quoted to two places from a three-place report figure
  ending in 5: 0.1447 → 0.145 → 0.15, and 0.34469 → 0.345 → 0.35.
  - Every bound figure in the draft is formatted from the raw JSON value, so the risk is confined to prose that
    copies a report's table.
  - Quoting from the JSON, not from a rounded table, would prevent it.
- **The probe could be a filing-day check.**
  - The draft's checklist re-runs its tests on filing day. A bound number can still drift, but an unbound one can
    be wrong with every test green, as finding 66's was.
  - The probe took about three minutes on four cores. It is not committed; this doc records the method.
- **The summary and `FINDINGS.md` are also outward-facing.** Their numbers were not probed. Few tests bind them,
  so most of their numbers would survive, and the probe would say little there.
- **`docs/RESUME_AFTER_RESTART.md`** quotes finding 66 in the measured direction (+4.97% to +9.19%), and is left as
  written.

## Verification

VERIFICATION
