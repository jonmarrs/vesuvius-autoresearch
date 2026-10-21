# Design and architecture review — the ScrollGT target exporter and the July benchmark report

Date: 2026-10-21. Baseline: `6a812697` (main after #166).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/export_fiber_targets.py`, which no review had read. It writes the fiber targets ScrollGT scores:
each cube's `skeleton.npz`, `mask.npz` and `meta.json`, whose `floors` it copies from a benchmark report. Also the
report it reads by default, `reports/fiber_benchmark_all_cubes.json`, and the documents that cite it.

Main has not moved since #166, and no owner PR is open.

## What changed

- **The exporter would ship floors from another scorer, or from another probability volume.**
  - `--bench` defaults to `reports/fiber_benchmark_all_cubes.json`, written 2026-07-30 and rerun 2026-08-16. That
    is scoring version 1. The scorer changed four times in October (`fibers/provenance.py`): versions 2, 3 and 4 on
    2026-10-04, the last taking ScrollGT's definition, and 5 on 2026-10-12 with its ERL fix (ScrollGT 0.7.0, its
    version 3, finding 85).
  - The report's rows carry no scoring version, and its cubes no provenance. Its numbers are not ScrollGT's:
    - connected components' merge-penalized ERL differs from ScrollGT's published row on all 11 cubes, and our
      tracer's on the 6 that have a row for it; the 5 other Scroll-5 cubes have none
      (`reports/tolerance4_rescore.json` holds ScrollGT's rows);
    - on `s1_00497_01497_03997_256`, our tracer's merge-penalized ERL is 23.16 against 19.22, and connected
      components' 37.13 against 34.04.
  - `export` writes `meta.json` fresh, floors included. Run as documented, it would replace ScrollGT's current
    floors on those 11 cubes with the July numbers.
  - It also took the mask from the probability file then on disk, while the floors came from the report. Nothing
    tied the two: a probability volume recomputed after the report would ship a mask the floors were not scored on.
  - **Change:** `bench_problems` names, per cube, why a report cannot supply its floors:
    - the report's `scoring_version` is not the current one, or a row was scored at another version;
    - there is no provenance;
    - the provenance's scoring version, probability hash, skeleton hash, tolerance or mask threshold is not this
      export's: the current version, the hashes of the `_fiberprob.npy` and `.nml` it ships, the report's tolerance,
      and 0.5.

    `bench_cli floors --all-cubes` records each of these, so a report it writes with this checkout passes.
  - `main` checks every cube before it writes any, and refuses with the reasons, so a refused report leaves the
    targets as they were. The committed report is refused on every cube.
- **The docs citing the July report as the full-cube numbers.** `docs/FIBER_TRACING.md` and
  `reports/fiber_connectivity_eval.md` now carry a dated note: the report is scoring version 1, its numbers are not
  ScrollGT's current rows (with the example above), and ScrollGT's `meta.json` holds the current floors.
- **Tests** (`tests/test_export_fiber_targets_bench.py`):
  - the committed report is refused on every cube;
  - a current report on the shipped files passes;
  - each mismatch is named alone: the report's version, a row's version, a row with none, no provenance, and the
    provenance's version, tolerance, threshold, probability volume and skeleton;
  - a cube missing from the report is refused too;
  - `main` refuses before exporting any cube when the last is refused, and exports all eleven once it is not.

  Each of these mutants is killed:
  - any one of the checks dropped: the report's version, the rows' versions, the probability hash, the skeleton
    hash, the tolerance or the threshold;
  - a missing provenance reported without the others;
  - only the first cube checked;
  - the refusal skipped.

## Verified, no change needed

- **The exporter's other checks:**
  - it refuses a cube whose semantic-label landing rate is below 0.999;
  - it refuses one whose scoreable-fiber count differs from the report's oracle row;
  - it refuses a shape mismatch;
  - its split is derived from the scroll, and refuses an unknown one.
- **`skeleton.npz`**: each fiber's edges are rebased onto the concatenated coordinates, with fiber and edge offsets
  to split them again.
- **`mask.npz`** packs the thresholded mask with its shape, so it unpacks to the scoring mask exactly.
- **`bench_cli floors --all-cubes`** writes everything the check reads: `scoring_version` at the top, each row's
  version from `as_row`, and each cube's provenance from `_measurement_provenance`.

## Observations for the owner (not changed)

- **Whether this exporter still writes ScrollGT's targets.** ScrollGT's published rows now carry its own scoring
  version 3. A report from this checkout's `bench_cli` records our version 5, the same definition under our
  numbering, so floors exported now would read 5 in ScrollGT's `meta.json`. The exporter also covers only the 11
  in-sample cubes, not the 10 held out. If ScrollGT now maintains its targets itself, the exporter could say so,
  or be retired.
- **`reports/fiber_benchmark_all_cubes.json` is kept as the July record.** Regenerating it needs the cubes, the
  model and a GPU, which this container has none of.

## Verification

- `pytest tests/test_export_fiber_targets_bench.py tests/test_export_fiber_targets_split.py`: 26 passed.
- Ruff, ruff format and mypy are clean on the changed files.
- No test reads either edited document.
- The standard suite, the smoke test and the independent review are recorded below once run.
