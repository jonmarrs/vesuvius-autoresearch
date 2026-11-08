# Scan-quality diagnostics: design and architecture review

Reviewed `measure_scan_quality.py` at base
`0824fa97` (the merge of #369). This review corrects an exploratory diagnostic;
it does not validate a scan-quality metric or add new research measurements.
Reproductions and CLI runs used synthetic arrays and temporary NRRD fixtures.

## Findings and repairs

1. **Tied intensities manufactured separability (P1).** Stable sorting assigned
   different ranks to equal intensities because positive-class samples were
   concatenated first. Constant CT scored folded AUC 1.0 instead of 0.5. A
   three-level quantized fixture scored 0.664275 instead of the pairwise tie
   oracle's 0.502392. Average tied ranks now give half credit for equality;
   ordering retains original intensity precision rather than first quantizing
   float64 to float32. Seed-0 balanced sampling and the population/cap rules
   remain explicit. The reported statistic is labeled as orientation-folded AUC,
   selecting its direction on the scored sample, not fixed-direction accuracy.
2. **The tensor feature depended on gradient orientation (P2).** The largest
   diagonal entry over trace is not the largest eigenvalue over trace. An
   axis-aligned linear field scored 1.0 while a diagonal one scored 1/3. The full
   symmetric tensor now includes cross terms; eigensolves operate plane-wise
   rather than allocating a whole-volume 3×3 matrix array.
3. **Correlations mishandled ties and undefined cases (P2).** Double argsort
   assigned artificial order within ties for Spearman; all-invalid outcomes
   could reach an empty minimum, and constant correlations could become NaN.
   Correlations now use tie-aware SciPy routines, pair counts, a minimum of four
   pairs, and explicit null/reason/status for insufficient or constant inputs.
4. **Mixed storage units contaminated texture comparisons (P2).** The earlier
   report already identified uint8/uint16 encoding differences. Feature inputs
   now use `/255` and `/65535`, respectively; floating input must already be
   finite in [0,1]. This removes storage-range differences, not acquisition or
   physical calibration differences.
5. **The CLI concealed incomplete work.** Missing pairs were skipped, fewer
   than four cubes returned success without the requested report, and raw JSON
   could contain NaN. A versioned report now records every selected cube,
   outcomes, feature values, counts, recipe and association statuses. Overall
   `MEASURED` requires every outcome and correlation to be defined;
   `INDETERMINATE` and `FAILED` exit nonzero. Input and output errors are explicit.

The initial three regression cases all failed before repair (constant AUC,
quantized tie oracle and tensor orientation). The earlier script had no curated
test module; the new one is registered in the validation runner.

## Architecture and workflow

Pure numerical functions cover volume validation, separability, features and
correlations. NRRD inspection/loading is separate from per-cube aggregation;
the CLI handles arguments, finite JSON and publication. Header shapes and
declared axis kinds are checked before either payload is decoded, with a default
256³-voxel bound. This is not an RSS bound or a lock against changing files.

The machine-specific default data directory is replaced by required `--data`.
JSON stdout and `--out` use the same `scan-quality-v2` object, replacing the old
human summary/bare list format. Publication reuses the existing staged-file
helper, requiring a new source-disjoint destination. The source root, resolved
cube directories and declared input paths are protected, including external
aliases and missing inputs. Writers must be serialized and source paths stable.
The report records paths/settings, not content hashes or immutable source bytes.

The old CT saturation/association conclusions in
`reports/scan_quality_reachability.md` are marked superseded and awaiting a
corrected dataset rerun. Original numbers remain as historical output; they are
not silently replaced with synthetic results. The mask-only characterization
and dtype observation are separate from the broken CT calculations.

## Validation

Python 3.10.21, NumPy 2.2.6, SciPy 1.15.3 and pynrrd, CPU only. Villa remains
pinned at `ccb431818fa68059138f2c964ae299fc474ff116` for the project smoke check.

- Affected curated selection: **146 passed in 13.59s**, across 4/184 modules
  (scan quality, volumetric labels, validation runner and suite guard).
- Final focused follow-up after external-alias publication protection:
  **36 passed in 1.79s**. Includes actual NRRD CLI/report publication from an
  external working directory, exit-0 four-cube completion, partial failures,
  missing data, all-undefined cases, pre-decode shape/budget/axis checks,
  source-disjoint outputs, tied ranks, exact AUC controls, float64 precision,
  equivalent uint8/uint16 encodings including byte order, and tensor orientation.
- Required smoke: **8/11 passed, 3 skipped, 0 failed in 11.8s**. Training-data
  checks lacked their local URI/labels; the optional batchgenerators transform
  was unavailable. Existing checkpoint loading and available model paths passed.
- Ruff lint/format and scoped Mypy passed all three changed Python files.
  Exact commands and captured outputs are recorded in the PR.

## Limits

No original 12/80-cube dataset rerun, full curated suite, full-scroll workload,
256³ performance/RSS benchmark, CUDA or native VC3D validation was performed.
The voxel limit bounds declared array size; feature and morphology work uses
multiple full-size arrays. Inputs are local trusted research files and must
remain stable during reads.

Morphology, gradients and smoothing operate in voxel coordinates; physical
spacing and registration are not established. Full tensors repair the missing
cross terms, but crop boundaries, resampling, arbitrary rotated grids and
unequal spacing can change results. Hand-annotation selection and the upward
chance bias from selecting AUC direction remain scientific limitations. A
complete descriptive report is not proof of useful scan-quality prediction,
independent validation or prize readiness.

Usage and schema/status migration: [Scan-quality diagnostics](SCAN_QUALITY.md).
