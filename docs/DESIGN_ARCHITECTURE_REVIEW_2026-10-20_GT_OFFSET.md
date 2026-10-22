# Design and architecture review — the ground-truth offset (#157) and the October draft (#158)

Date: 2026-10-20. Baseline: `1dc3cb65` (main after #158).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- **The owner's #157.** It re-runs `scripts/neural_tracer_placement.py` with the field #154 added
  (`median_disp_perp_zyx`). It also adds `scripts/neural_tracer_gt_offset.py`, its test, its JSON, and a bullet in
  `reports/neural_tracer_entrant.md`: "the GT sits about a voxel off the CT's fibers on 5 in-sample cubes".
- **The owner's #158**, which folds finding 93 and that measurement into `docs/PRIZE_FILING_2026-10_DRAFT.md`.

The owner's open #159 (night cycles) and #160 (ScrollGT 0.8.2 in the draft) are not touched. Neither is any file they
change.

## What changed

- **Nothing in #157 or #158.** No defect was found; what was checked is below.
- **The 2026-10-20 placement-shift review's observation** said the question was open until the placement script ran
  again. #157 ran it. A dated follow-up line there points here.

## Verified, no change needed

- **The re-run placement JSON.** Every field #151 recorded is unchanged, on every cube and entrant, with only
  `median_disp_perp_zyx`, `n_perp_zyx` and the top-level `perpendicular` added. #157's commit says the same.
- **`neural_tracer_gt_offset.py` is built so that no check grades itself.**
  - **Cross-entrant.** It moves one entrant's centreline by the other's shift, so the tested entrant's own data does
    not set the correction. The opposite shift is the control.
  - **The CT check.** It reads the smoothed CT along the entrants' direction only, from t = −1 to 2. An interior peak
    marks a ridge displaced along that direction. A plain intensity gradient would put the peak at an end.
  - **Matched samples.** It matches against the same GT samples as the placement measure (`gt_points` is
    `gt_samples`' points, tested).
- **The report's and the commit's figures**, recomputed from `neural_tracer_gt_offset.json` and
  `neural_tracer_placement.json`:

  | figure | value |
  |---|---|
  | the 5 cubes' mean shift | 1.01–1.53 voxels |
  | other in-sample cubes | at most 0.78 |
  | Scroll 3 | at most 0.72 |
  | this tracer, moved by the generator's shift | gains 0.056–0.086 |
  | the same, on Scroll 3 | gains 0.004–0.017 |
  | the opposite shift | loses 0.155–0.229 |
  | the generator, moved by this tracer's shift | gains 0.053–0.104 |
  | the CT's t* | 0.5–0.75, interior on all 5 |
  | t* × \|shift\| | 0.51–0.93 |
  | CT gains | 0.11–1.06 grey levels |
  | corrected shares | 0.52–0.66 |
  | Scroll 3's shares | 0.68–0.76 |

  The entrants' shifts agree in sign wherever either reaches 0.5 voxels on all 21 cubes, not only on the 5.
- **The seeding analysis's seed counts and the probe's** are counted the same way: `tiles.jsonl`'s `dots`, the last
  line per tile. So the manipulation check compares like with like.
- **#158's sentences** trace to the reports, and `tests/test_filing_2026_10_numbers.py` pins them:
  - finding 93's 0.63 → 0.67, 0 of 8, 0.88 and 7 of 8;
  - the 2.71× and 2.12× and their 1.26× and 0.81× at tolerance 4;
  - the 0.51–0.93 offset and the 0.06–0.09 recovery;
  - 21 failed predictions (18 before, and finding 93's three).

  The draft's "Not 'ScrollGT's ground truth is wrong on five cubes'" states the limit.
- **Tests.**
  - `tests/test_neural_tracer_gt_offset.py`, `test_neural_tracer_placement.py` and `test_neural_tracer_entrant_report.py`:
    32 passed.
  - The filing, seeding-report and pitch-report tests: 36 passed, 4 skipped for want of the sibling checkouts.
- **Ruff's bug-finding rules on the rest of the repository.** These are undefined names, redefinitions, loop-variable
  capture, mutable defaults and invalid comparisons.
  - They are clean on `scripts/`, `src/` and the top-level modules.
  - The hits in `repro/` are villa's preserved scripts, kept as they are, and read-only defaults in the GP-winner
    reproduction.

## Observations for the owner (not changed)

- **The CT finds a smaller offset on most other cubes too.** Along the entrants' direction it peaks inside the range
  almost everywhere:
  - **Scroll 3:** at t* > 0 on 7 of 8 cubes, putting the fibers' centres 0.18–0.48 voxels off the GT;
  - **the held-out cubes:** 0.18 and 0.21;
  - **two more in-sample cubes**, outside the 5: 0.51 and 0.97 off, where the entrants' shifts are under a voxel
    (t* 1.25 and 1.875).

  So the 1-voxel cut on the entrants' shift picks the 5 largest offsets, not the only ones. The report's "on 5 of the
  11 in-sample cubes" is the cut's count. A GT that sits a fraction of a voxel off the CT may be general, and
  larger in sample.
- **The corrected comparison sets corrected in-sample shares against Scroll 3's uncorrected ones.** Moved the same
  way, Scroll 3's shares rise by 0.004–0.017, so the like-for-like gap is a little larger. The conclusion, "part of
  the gap, not all", holds either way.
- **The CT's gains are small** next to its spread (0.11–1.06 grey levels against standard deviations of 22–49). The
  interior peaks are what carry the check.
- **`mean_shift` would raise a bare TypeError** for a cube where an entrant has no samples across some axis (its
  `median_disp_perp_zyx` holds None there). Every cube has them today.

## Verification

- `pytest tests/test_neural_tracer_gt_offset.py tests/test_neural_tracer_placement.py
  tests/test_neural_tracer_entrant_report.py`: 32 passed.
- `pytest tests/test_filing_2026_10_numbers.py tests/test_neural_tracer_seeding_report.py
  tests/test_neural_tracer_pitch_report.py`: 36 passed, 4 skipped.
- The figures above were recomputed from the committed JSONs, independently of the tests.
