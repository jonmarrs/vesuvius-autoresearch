# Design and architecture review — the placement measure's shift test, and the loop's dead code

Date: 2026-10-20. Baseline: `b28d6a51` (main after #151).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- **The owner's #151**: `scripts/neural_tracer_placement.py`, its test, and the exploratory section it adds to
  `reports/neural_tracer_entrant.md`. It finds that the thin entrants' Scroll-3 lead is placement within 2–4 voxels.
- **What ruff's wider rules find in the loop's modules** (`run_autoresearch_loop.py`, `scripts/training/`). The
  repository's own ruff settings pass there.

## What changed

- **The placement measure's shift test could miss a shift.**
  - The report rules out a shift between the GT and the CT because the median displacement from centreline to GT is
    at most 0.62 voxels along any axis, on every cube.
  - The displacement to a centreline sample's nearest GT point is perpendicular to the GT fiber. So a shift along a
    fiber does not show on that fiber: a z shift leaves a fiber that runs along z with no z displacement. Where most
    of a cube's matched samples lie on fibers along one axis, the median along that axis reads about 0 whatever the
    shift there.
  - The new test builds three fibers along z and one across it. A 2.5-voxel z shift of the GT puts a quarter of the
    samples beyond 2 voxels, and the median z displacement stays at exactly 0.
  - On randomly placed in-plane arcs and fibers along z (a check not committed), a 2-voxel z shift lowered the share
    within 2 voxels from 1.00 to 0.75–0.89. The median z displacement read at most 0.1.
  - The other axes are not safe either: a cube whose in-plane fibers mostly run along x would hide an x shift the same
    way.
  - **Change:**
    - `gt_samples` also returns each GT sample's edge direction, NaN for an edge of length 0.
    - `placement` also records `median_disp_perp_zyx`, the median displacement along each axis over the samples on
      fibers within 30° of perpendicular to it (|cos| ≤ 1/2). Those samples keep at least 3/4 of a shift along that
      axis. It also records their counts, `n_perp_zyx`, and the threshold, `perpendicular`.
    - The fields `#151` recorded are unchanged.
  - **The committed run predates the new fields**, and the runs and ScrollGT's data are not in this container. So the
    report now says what the median does and does not exclude, in its own bullet and in the summary that cites it.
    The 0.62 and every other number in the section are unchanged.
- **Tests** (`tests/test_neural_tracer_placement.py`):
  - the shift case above, a shift along x, and the unshifted case;
  - the edge direction, and NaN for an edge of length 0.

  The owner's tests now unpack `gt_samples`' fourth array. Each of these mutants is killed:
  - the perpendicular mask inverted;
  - every sample counted, or the threshold at 1;
  - the median taken along the wrong axis;
  - a zero direction for an edge of length 0.
- **Dead code in the loop and the trainer.**
  - `run_autoresearch_loop.main` set `end_hour` and never read it. The shift-end check that used it was replaced
    after the 2026-05-20 overrun; the comment there records the old check.
  - `train.py` imported `torch.nn` and `AuxiliaryConfig` without using them. No module reaches either through `train`.
  - `ExperimentConfig.pinned` said the loop would not evolve a pinned config. Nothing reads it: it marked the
    GP-winner baseline that the loop injected every 10th cycle (`6bd6094d`), and that injection has since been removed.
    The comment now says so. The field stays, because `from_json` refuses an unknown key and `config.json` and the
    checkpoints record it.

## Verified, no change needed

- **#151's numbers.**
  - Its tests recompute every figure the section quotes from `neural_tracer_entrant.json` and
    `neural_tracer_placement.json`.
  - With 8 cubes against 3, the exact two-sided rank test's smallest p is 2/C(11, 3) = 0.012, as quoted.
  - The groups are finding 91's: 11 in-sample cubes (5 from Scroll 1, 6 from Scroll 5, three of them 512³), 8 on
    Scroll 3 and 2 held out on Scroll 5.
  - The sampling is `afv_to_labels.rasterize`'s, at 0.25 voxel. Two differences:
    - `predicted` keeps samples in [0, size), while the rasteriser keeps those that round into the cube, a
      half-voxel shell more at each face;
    - the distances are to the samples themselves, not to the voxels they label.
  - The near-node and mid-edge split measures the distance along the edge from its nearer node, and the tests pin it.
- **The loop's broad `except Exception`s** (7 in the loop, 10 in `train.py`). Each one logs. The validation metrics,
  the topology threshold and the batchgeneratorsv2 fallback count theirs into `run_result.json`. The curve probe's
  are inside a probe that must not end a 12-hour run.
- **The batchgeneratorsv2 path returns the Albumentations path's shapes:** ink (B, 1, H, W) and the fiber target
  (B, 1, 1, H, W).
- **The loop's tweak axes all reach training.** The ones that need a setting are gated on it:
  - dropout on gated_unet;
  - the heads' loss weights on their heads;
  - UA-MT's weight and decay on `use_uamt`.

  Production sets `unlabeled_uris`, so UA-MT runs.
- `max_prize_skel_dist` is read by nothing, on purpose: the field's comment and `evaluate_prize_gates` say the
  skeleton distance is reported, not gated.

## Observations for the owner (not changed)

- Whether a shift explains part of the in-sample deficit is open until the placement script runs again on the work
  directories. The new field would show a shift that the matched fibers' directions hide from the plain median.

## Verification

- `pytest` on the placement, entrant-report, pitch, and filing-number tests: 62 passed, 4 skipped for want of the
  sibling checkouts.
- Ruff and ruff format are clean on the changed files. Mypy is clean on them, the test included. With
  `--warn-unused-ignores`, the loop and `train.py` report the same 13 unused ignores as on main, and the changed
  files none.
