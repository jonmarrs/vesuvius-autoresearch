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
  - #165 tested `tolerance4_rescore.main()` the same way, with ScrollGT stubbed.
- **Tests** (`tests/test_octant_crop_rescore.py`, +7).
  - **Six run `main()` end to end**, with these stubbed:
    - ScrollGT's `score_tracing` and `load_fiber_target`;
    - the `.afv` reader and rasterizer;
    - the saved instances.

    Each labelling marks every octant's first voxel with its index, and each cube's ground truth has one fiber per
    octant. The stub checks that:
    - the whole cube is scored on the cube's own uncropped ground truth;
    - each octant gets only that octant's voxels and that octant's fiber, shifted;
    - the `.afv` read and the instances loaded are the current cube's;
    - the tolerance is passed by keyword.

    Finding 94's reference rows differ by entrant and by cube, and each octant scores differently, so each row must
    land under its own `z_y_x` key.
    - One test checks the whole cubes, every octant of every cube for both entrants at both tolerances, the verdict,
      and the JSON.
    - Four cases move one compared field of one entrant's whole-cube row, up or down: ERL, coverage, instance count
      and predicted length. Each must give IDENTITY_FAILED, exit 1, name that field on every cube, and write no
      verdict.
    - One test checks that another scoring version is refused.
  - **One tests the crop.** A fiber crossing a face is kept by both octants with the right coordinates. A node between
    255 and 256 lies in neither. The input skeleton is left unchanged.
- **Mutants.** Each of these makes at least one new test fail. Without the new tests, every one passed:
  - in the identity check:
    - no problem recorded;
    - one field compared;
    - a one-sided comparison;
    - the entrants' reference rows swapped;
    - the first cube's reference used for every cube;
  - in the labellings: the first cube's `.afv`, or the first cube's instances, used for every cube;
  - in the scoring:
    - an octant scored on the whole labelling or on the whole skeleton;
    - every octant at tolerance 4;
    - the tolerance passed positionally;
    - the whole cube scored on a cropped skeleton;
    - the scoring version unchecked;
  - in the crop: a fiber shifted in place, so that later octants see shifted coordinates;
  - in the keep rule: `c < size` in place of `c <= size - 1`;
  - in the JSON: the octant key written in x, y, z order.

## Verified, no change needed

- **The script is the registered one.**
  - It was committed with the registration and its tests at `b5acd9bb`, 00:28:21 PDT.
  - None of them changed before the result. The registration gained only its "Run …" status line.
  - The run's start, 00:29, is the owner's statement. Neither git nor the JSON records it.
- **The script implements the registration:**
  - the three in-sample 512³ cubes, and eight octants at offsets 0 and 256;
  - tolerances 4 and 2;
  - a fiber kept where at least two nodes lie inside, by ScrollGT's `0 <= c <= size - 1`;
  - the four identity fields, compared exactly;
  - the 16 and 8 thresholds, with ties not counted as a lead;
  - the readings word for word;
  - exit 0 only for `OK`.
- **The report's figures are the JSON's:**
  - at tolerance 4: medians 45.28 and 38.67, a ratio of 1.08 (0.85–1.64), and leads on 19 of 24 (7, 6 and 6 by cube);
  - at tolerance 2: 9.88 and 20.52, 0.46 (0.37–0.63), and no lead;
  - a median of 132.5 ground-truth fibers per octant;
  - a whole-cube ratio of 1.13.

  The whole-cube rows equal finding 94's on all ten kept fields, not only the four checked.
- **The scroll claim.** The three Scroll-5 256³ cubes whose finding-94 rows the report quotes are the in-sample
  ones, beside the five Scroll-1 cubes. The rows are 21.10 against 42.82, 24.30 against 56.52 and 23.09 against
  34.43. The paragraph added to `tolerance4_rescore.md` agrees.
- **The paths** follow `tolerance4_rescore.py` and `neural_tracer_analysis.py`: the owner's machine paths.

## Observations for the owner (not changed)

- **The identity check does not run the crop path.**
  - The whole cube is scored on the loaded skeleton and labels. Every octant is scored through `crop_skeleton` and
    `crop_labels`.
  - `crop_skeleton` takes shallow copies of ScrollGT's skeleton and fiber objects and replaces only `coords`.
    Anything else on them that depends on position would carry into every octant unchanged: a cached value, a stored
    shape, an `origin_zyx`.
  - Neither the identity check nor the registration's `in_bounds_mask` comparison, which compares only the fibers
    kept, would see that.
  - The crops also keep a kept fiber's outside nodes, some at negative coordinates. Whether the scorer ignores those
    nodes, as the registration says, or clips them, needs ScrollGT's code. This review had none.
  - Scoring the whole cube through `crop_skeleton(skel, (0, 0, 0), 512)` and `crop_labels(…, 512)` would put the
    identity check on the same path. The script is registered and has run, so whether to check this is the owner's
    call.
- **A node between 255 and 256 on an axis belongs to neither octant.**
  - The keep rule is ScrollGT's `0 <= c <= size - 1`, so a node at 255.5 falls outside both neighbouring octants.
  - That matches the rule a real 256³ cube's ground truth is kept by. The registration checked it against
    `in_bounds_mask` on all 24 octants.
  - Noted because finding 95 reads the crops as the 256³ scoring scale.
- **The report leaves out descriptives the registration lists.**
  - The registration lists per-cube medians, coverage and merges. At tolerance 4, by cube:

    | cube | merge-penalized ERL, neural / ours | paired median ratio | coverage, neural / ours | merges, neural / ours |
    |---|---|---|---|---|
    | `s5_06494_01994_03994_512` | 55.98 / 56.00 | 1.09 | 0.61 / 0.85 | 21.5 / 64.5 |
    | `s5_06994_00994_04994_512` | 38.09 / 36.29 | 1.07 | 0.57 / 0.77 | 60.0 / 130.0 |
    | `s5_07994_01994_05494_512` | 43.53 / 37.08 | 1.17 | 0.58 / 0.78 | 33.0 / 67.0 |

  - On the first cube the medians are level, though the neural tracer leads on 7 of its 8 octants.
- **The report's "What it means" goes past the registered reading.**
  - For P1 holding, the registration's reading ends "What remains is their scroll (mostly Scroll 1) and annotation".
  - The report adds "It is not the scroll alone either" and "What separates a real 256³ cube from an octant is that
    the tracer ran on it", on three cubes. The next sentence notes that content and annotation differ too.
  - It is not marked as beyond the registration.
- **Smaller points:**
  - The JSON does not record the scoring version, which `tolerance4_rescore.json` does.
  - Each crop is made once per tolerance, so twice.
- **The octant tests are outside the standard suite**, like the other neural-tracer studies' tests. They run under
  `pytest tests/`.

## Verification

- `pytest tests/test_octant_crop_rescore.py tests/test_octant_crop_report.py`: 21 passed, 7 of them new.
- Ruff 0.9.10 `check` and `format` are clean on the test file, which was formatted before. The owner's tests are
  unchanged.
- **The standard suite** on the first commit (`852f5cf9`) ran as on main: 2704 passed, with the same 42 failures and
  2 errors, all environmental. No test in it imports this script. The smoke test gave 9 of 11 passed and 2 skipped,
  as on main.
- **Independent review** of the first commit, in a worktree without villa or ScrollGT. It found nothing blocking.
  - It confirmed:
    - the stubs' call shapes and order match `main()`;
    - the script was committed with the registration, and the script matches it;
    - every figure in the report and in the paragraph added to `tolerance4_rescore.md`;
    - the tests peak at about 90 MB, since only marked and copied pages are touched.
  - Its should-fix findings:
    - a crop that shifted fibers in place passed every test;
    - the identity stubs were uniform across entrants and cubes, and moved fields up only, so a one-sided comparison,
      swapped references, or the first cube's files for every cube passed;
    - the identity check does not run the crop path.
  - Its nits:
    - the descriptives the registration lists, and the report's reading;
    - the only octant key checked read the same in either order;
    - the 255–256 boundary was not pinned;
    - the tolerance could be passed positionally;
    - the count of mutants;
    - "the report names" the Scroll-5 cubes, where it quotes their figures;
    - the scoring version and the double crop.

  The first two should-fix findings are fixed in the tests. The third, the descriptives and the reading are recorded
  above, as is the smaller script tidiness. The other nits are fixed. The test helper's `in_bounds_mask`, which goes
  stale on a cropped fiber and which nothing calls, is the owner's and is left as is.
