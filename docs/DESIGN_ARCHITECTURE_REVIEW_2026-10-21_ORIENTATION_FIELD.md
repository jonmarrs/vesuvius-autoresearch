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
    result would say so.
  - **Change:** `probability()` refuses a volume with no record, or whose hash is not the record's, and names
    the file. Each row now records the volume's hash and the record's `inference` identity.
- **The field was the tracer's in float32, not float64.**
  - The driver says it builds the field "exactly as `bench_cli.cmd_trace` does". `cmd_trace` takes
    `_fiber_prob`'s float64 copy, while the driver passed the float32 file, and `hessian` keeps a float input's
    precision.
  - On a synthetic 64³ volume of blurred tubes, the two fields differ by at most 0.001° on fiber voxels, and in
    no voxel's validity. So the committed results stand.
  - **Change:** the driver casts to float64, as `_fiber_prob` does, so the claim holds exactly.
- **An undefined correlation was written as `NaN`.** With a constant error or curvature (a straight fiber),
  `np.corrcoef` gives NaN, which `json.dumps` writes as the invalid token `NaN`. It is now `null`. The committed
  JSON has none.
- **`local_curvature_deg`'s docstring** said the mod-180 fold made only a 180° hairpin read as straight. It
  reads every turn θ above 90° as 180° − θ, so a 135° turn as 45°. The docstring now says so.
  - The report's medians (11.6–19.4°) are far below 90°, so its curvature findings are unaffected.
  - Only the node-aligned correlation could move, and only through the rare turns past 90°.
- **Tests** (`tests/test_analyze_orientation_field.py`, new). A 16³ cube with a straight fiber is used to check
  that:
  - a row records the attested volume's hash and identity;
  - the field is built in float64 at `gauss_sigma=2, sigma=3`;
  - the field follows the fiber (median error under 10°);
  - an undefined correlation is `null`, and the row serializes without NaN;
  - a volume its record does not attest, or with no record, is refused.

  Each of these mutants is killed:
  - the float64 cast dropped;
  - the hash check skipped;
  - the record check skipped;
  - the provenance left out of the row;
  - NaN written again.

## Verified, no change needed

- **`angular_error_deg`** compares orientations: it takes the absolute cosine, so a flipped eigenvector scores 0°.
- **`sample_field`** looks up the nearest voxel, as the walker's `_direction_at` does. It reports out-of-bounds
  positions as undefined rather than clipping them.
- **`local_curvature_deg`** and the tangents come from the edge graph, not the NML's array order.
- **The report's secondary cut** compares error and curvature node by node. Both come from `analyse_cube` in the
  same node order.
- **`tests/test_field_quality.py`**: 42 tests, passing.

## Observations for the owner (not changed)

- **A cube cached before the record existed** is now refused until `bench_cli` recomputes its cache. Any cube
  `bench_cli` has run on since 2026-10-04 has a record.
- **The driver covers the six 256³ cubes of its 2026-08-02 study.** It leaves out the five Scroll-5 cubes added on
  2026-08-16: two 256³, and three 512³, whose dense Hessian needs the tiled path. That is the study's design.

## Verification

- `pytest tests/test_analyze_orientation_field.py tests/test_field_quality.py`: 45 passed, the new file with
  RuntimeWarnings as errors.
- Ruff, ruff format and mypy are clean on the changed files.
- The standard suite, the smoke test and the independent review are recorded below once run.
