# Design and architecture review — the owner's #170, the octant-crop rescoring (finding 95)

Date: 2026-10-21. Baseline: `78be44a0` (main after the owner merged #170).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: #170, as merged.
- `docs/preregistration/2026-10-21_octant_crop.md`;
- `scripts/octant_crop_rescore.py` and its tests;
- `reports/octant_crop_rescore.{json,md}`;
- the paragraph it adds to `reports/tolerance4_rescore.md`.

The study cuts the three in-sample 512³ cubes into their 256³ octants. It scores villa's neural tracer and our tracer
on each octant, at tolerances 4 and 2. P1, a lead on at least 16 of the 24 octants at tolerance 4, held on 19.

This round covers the 17:12 UTC firing.

## What changed

- **`main()` was untested, and it holds the study's guard.**
  - The tests covered the crop helpers, the verdict's thresholds, ties, the status and the report's figures.
  - `main()` builds the identity check, and no test called it. That check is the registration's IDENTITY_FAILED
    rule: each whole cube must reproduce finding 94's merge-penalized ERL, coverage, instance count and predicted
    length for both entrants.
  - `main()` also crops each labelling and the ground truth to each octant, scores both tolerances and writes the
    JSON.
  - So any of these changes would have passed every test:
    - recording no identity problem;
    - comparing one field only;
    - scoring an octant on the whole labelling or the whole skeleton;
    - scoring every octant at tolerance 4;
    - skipping the scoring-version check.
  - #165 tested `tolerance4_rescore.main()` the same way.
- **Tests** (`tests/test_octant_crop_rescore.py`, +6) run `main()` end to end, with these stubbed:
  - ScrollGT's `score_tracing` and `load_fiber_target`;
  - the `.afv` reader and rasterizer;
  - the saved instances.

  Each labelling marks every octant's first voxel with its index, and each cube's ground truth has one fiber per
  octant. The stub scorer asserts that each octant gets only that octant's voxels and that octant's fiber, shifted.
  - **One test** checks the whole cubes at tolerance 4, every octant of every cube for both entrants at both
    tolerances, the verdict, and the JSON layout.
  - **Four cases** change one compared field of one entrant's whole-cube row: ERL, coverage, instance count and
    predicted length. Each must give IDENTITY_FAILED, exit 1, name that field on every cube, and write no verdict.
  - **One test** checks that another scoring version is refused.
  - Each mutant above fails at least one of them.

## Verified, no change needed

- **The script is the registered one.**
  - It was committed with the registration at `b5acd9bb`, 00:28:21 PDT. The run began at 00:29.
  - Neither file changed before the result. The registration gained only its "Run …" status line.
- **The script implements the registration:**
  - the three in-sample 512³ cubes, and eight octants at offsets 0 and 256;
  - tolerances 4 and 2;
  - a fiber kept where at least two nodes lie inside, by ScrollGT's `0 <= c <= size - 1`;
  - the four identity fields, compared exactly;
  - the 16 and 8 thresholds, with ties not counted as a lead;
  - the readings word for word.
- **The report's figures are the JSON's:**
  - at tolerance 4: medians 45.28 and 38.67, a ratio of 1.08 (0.85–1.64), and leads on 19 of 24 (7, 6 and 6 by cube);
  - at tolerance 2: 9.88 and 20.52, 0.46 (0.37–0.63), and no lead;
  - a median of 132.5 ground-truth fibers per octant;
  - a whole-cube ratio of 1.13.
- **The scroll claim.** The three Scroll-5 256³ cubes the report names are the in-sample ones, beside the five
  Scroll-1 cubes. Their finding-94 rows are the ones it quotes: 21.10 against 42.82, 24.30 against 56.52 and 23.09
  against 34.43.
- **The paths and exit codes** follow `tolerance4_rescore.py` and `neural_tracer_analysis.py`: the owner's machine
  paths, and exit 0 only for `OK`.

## Observations for the owner (not changed)

- **A node between 255 and 256 on an axis belongs to neither octant.**
  - The keep rule is ScrollGT's `0 <= c <= size - 1`, so a node at 255.5 falls outside both neighbouring octants.
  - That is how ScrollGT would load a real 256³ cube, so the crop mirrors one. The registration checked it against
    `in_bounds_mask` on all 24 octants.
  - Noted only because finding 95 reads the crops as the 256³ scoring scale.
- **The octant tests are outside the standard suite**, like the other neural-tracer studies' tests. They run under
  `pytest tests/`.

## Verification

- `pytest tests/test_octant_crop_rescore.py tests/test_octant_crop_report.py`: 20 passed, 6 of them new.
- The six mutants above each fail at least one new test, and none fails an old one. No old test calls `main()`.
- Ruff 0.9.10 `check` and `format` are clean on the test file, which was formatted before.
