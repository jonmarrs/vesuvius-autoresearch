# Design and architecture review — the orientation-field measure and its driver

Date: 2026-10-21. Baseline: `9f64a3c8` (main after #168).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `src/vesuvius_autoresearch/fibers/field_quality.py` (692 lines, one earlier mention in these reviews) and
`scripts/analyze_orientation_field.py`, which no review had read and no test covered. Together they produced
`reports/fiber_orientation_field_quality.md`: how well `fiber_hz_vt`'s Hessian orientation field follows the
hand-traced fibers.

Main has not moved since #168, and no owner PR is open.

## What changed

- **The driver used whatever probability volume was on disk.**
  - It loaded `<cube>_fiberprob.npy` directly. `bench_cli._fiber_prob` writes a cache record beside it,
    `<cube>_fiberprob.json`, naming the model, patch and device that produced it and the volume's hash, and uses
    the cache only when that record attests it. The driver checked neither.
  - So a volume from another model or patch size, or one rewritten since, would be measured, and nothing in the
    result would say so. The cache is one file per cube, which any `bench_cli` run with another model, `--patch`
    or `--device` overwrites, so six cubes could mix recipes.
  - **Change:**
    - `probability()` refuses a volume that its record does not attest: no record, an unreadable or malformed one,
      or another hash. It also refuses a volume `_fiber_prob` would not accept: not float, not finite, or outside
      [0, 1]. Each refusal names the cube and the `bench_cli floors --cube` command that rebuilds the cache.
    - Each row records the volume's hash and its identity: the inference version, the image, the model's files and
      the recipe. The model's directory, a path on the machine that ran it, is left out.
    - `main()` refuses to write when the cubes' volumes differ in inference version, model files or recipe, and
      names each cube's.
- **The field was the tracer's in float32, not float64.**
  - The driver says it builds the field "exactly as `bench_cli.cmd_trace` does". `cmd_trace` takes
    `_fiber_prob`'s float64 copy, while the driver passed the float32 file, and `hessian` keeps a float input's
    precision.
  - On synthetic volumes of blurred tubes, the two fields differ by 0.001-0.002° on fiber voxels (64³ and 128³,
    clean and noisy). Only a few background or boundary voxels change validity or eigenvector, and none on a fiber.
    So the precision does not move the committed results.
  - **Change:** the driver casts to float64, as `_fiber_prob` does, so the claim holds exactly.
- **A row could hold `NaN`, which `json.dumps` writes as an invalid token.**
  - With a constant error or curvature (a straight fiber), the correlation is NaN.
  - With no scored node, so are the error percentiles, the over-25° fraction and the estimator disagreement.
  - Every non-finite number in a row is now `null`, and the report is written with `allow_nan=False`.
  - The committed JSON has none.
- **`local_curvature_deg`'s docstring** said the mod-180 fold made only a 180° hairpin read as straight. It
  reads every turn θ above 90° as 180° − θ, so a 135° turn as 45°. The docstring now says so, and that an
  equal-edge hairpin is left out as degenerate.
  - Folding lowers a turn over 90°. It can move a node across the median turn (11.6–19.4° per cube) only if the
    turn is above about 160°, a near-hairpin. Real hand traces rarely double back between nodes, but the folded
    data cannot show how rarely.
- **The report's "Reproducing" section** now notes the cache record step. Its committed numbers predate the record
  (2026-10-04), so a rerun recomputes the volumes under that date's inference code and need not reproduce them.
- **Tests** (`tests/test_analyze_orientation_field.py`, new, with RuntimeWarnings as errors). A 16³ cube with a
  straight fiber, its own size and origin parsed from the stem, is used to check that:
  - a row records the attested volume's hash and identity, without the model's directory;
  - the field is built in float64 at `gauss_sigma=2, sigma=3`;
  - the field follows the fiber (median error under 10°);
  - an undefined correlation is `null`;
  - a measurement with no scored node serializes with nulls;
  - each of these is refused, naming the command:
    - a volume its record does not attest;
    - no record, a corrupt one, or one that is not a record;
    - a record without a hash;
  - a volume outside [0, 1], or of another size, is refused;
  - `main` writes two cubes from one model and recipe, and refuses two whose patch, device, model files or
    inference version differ, writing nothing.

  Each of these mutants is killed:
  - the float64 cast dropped;
  - the hash check, the record checks, the range check or the recipe check skipped;
  - the provenance left out;
  - NaN written again;
  - the correlation's warning let through.

## Verified, no change needed

- **`angular_error_deg`** compares orientations: it takes the absolute cosine, so a flipped eigenvector scores 0°.
- **`sample_field`** looks up the nearest voxel, as the walker's `_direction_at` does. It reports out-of-bounds
  positions as undefined rather than clipping them.
- **`local_curvature_deg`** and the tangents come from the edge graph, not the NML's array order.
- **The report's secondary cut** compares error and curvature node by node. Both come from `analyse_cube` in the
  same node order.
- **`tests/test_field_quality.py`**: 42 tests, passing.

## Observations for the owner (not changed)

- **A cube cached before the record existed** is now refused until `bench_cli` recomputes its cache. Any cube that
  `bench_cli trace`, `floors` or `score --with-floors` has run on since 2026-10-04 has a record.
- **The driver covers the six 256³ cubes of its 2026-08-02 study.** It leaves out the five Scroll-5 cubes added on
  2026-08-16: two 256³, and three 512³, whose dense Hessian needs the tiled path. That is the study's design.

## Verification

- `pytest tests/test_analyze_orientation_field.py tests/test_field_quality.py`: 56 passed.
- Ruff, ruff format and mypy are clean on the changed files.
- **The standard suite** on the first commit (`94438898`) ran as on main: 2690 passed, with the same 42 failures and
  2 errors, all environmental. It does not include the driver's tests. The smoke test gave 9 of 11 passed and 2
  skipped, as on main.
- **Independent review** of the first commit found nothing blocking. It confirmed:
  - the record's format and hash;
  - the float64 path;
  - the fold;
  - the first commit's mutants;
  - each date and count in this document.

  It re-measured the precision difference itself, and found it a little larger than first stated (above).

  Its should-fix findings:
  - the record's identity went unchecked, so cubes could mix recipes;
  - NaN could still reach the JSON from six other fields;
  - this document did not say that a rerun recomputes the volumes.

  Its nits:
  - the precision figures;
  - the RuntimeWarning claim;
  - two surviving mutants;
  - the unneeded size patch;
  - a corrupt record's traceback;
  - the fold's median argument;
  - the equal-edge hairpin;
  - which `bench_cli` commands write a record;
  - this placeholder.

  All are addressed above. Not addressed: the hash-then-load window, which `bench_cli` shares, and factoring one
  attested loader out of `bench_cli` and the driver.
