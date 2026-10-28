# Patch input checks design and architecture review — 2026-10-28

Reviewed the downstream selection and spatial checks against main
`16aea93032aaed044e149363b49d0f3b3e228b65` (PR #282). Scope: input interpretation,
failure behavior, descriptive statistics, reporting and integration with patch
dataset preparation. Work used synthetic data in an isolated checkout; no live
study journals/results, historical dataset rebuilds, GPU jobs, research deployment
or prize filing were performed. Before publication, main advanced to
`864be09b9dd595ea4719633a2aaa46e6206786fe` (PR #278). Its seven disjoint file
updates were preserved in this checkout and the combined tree was revalidated.

## Findings and fixes

- **Names could pass without usable patch directories.** The selection checker
  counted names from `verified_patches/`, including dangling symlinks. Shared
  membership captures now require directories and record canonical targets.
  Membership and link mappings are rechecked before successful reports return.
- **Nonfinite/ambiguous inputs could bypass gates.** NaN areas made the area-gap
  comparison false and could yield a PASS. Both checkers now reuse the bounded,
  strict reference parser from dataset preparation. Duplicate IDs/fields, unsafe
  IDs and invalid numeric domains fail. Aggregate area totals are validated too:
  finite fields can overflow under a different summation order in Python 3.10.
- **Empty and singleton selections crashed statistics.** Empty/zero-area arms
  produce failed input checks. Undefined statistics are null (`n/a` in text),
  including singleton quartiles; the existing exclusive quartile method remains
  for larger sets. A valid singleton can pass mechanical checks without a
  statistical-power claim.
- **Small/weighted populations could not define all bands.** The one-cut-per-patch
  loop returned too few cuts, and area spreading indexed past the boundary list.
  Weighted cuts now repeat when a patch crosses several quantiles, producing
  exactly the requested count and flagging repeated cuts. Ordering ties by ID
  makes the axes stable; spreading conserves area. Point extents exactly on a
  cut keep the legacy lower-band convention.
- **Missing/conflicting geometry could bias diagnostics silently.** Spatial
  measurement now requires complete arm geometry and agreement for shared IDs.
  Optional ALL requires geometry for the entire scored reference population on
  the same union-derived axes. Geometry captures are checked before reporting.
- **Text included unsupported interpretations.** The global area gap was
  hardcoded to 0.01 points, and the outermost proxy band was equated with scored
  windings. The report now prints the actual reference-normalized area gap and
  labels radial proxies without inferring winding calibration or spatial balance.
- **Only human-oriented output was available.** Both CLIs support `--json` with
  finite, scoped reports and meaningful exit status. Default text remains, with
  usable failure reasons rather than statistics tracebacks.

All six original regressions failed on the baseline: dangling-link acceptance,
NaN area acceptance, singleton/empty crashes, missing radial cuts and the
hardcoded gap. Captured result: **6 failed in 0.23s**. Further tests cover strict
JSON, exact CLI exit/status semantics, complete/conflicting geometry, full-source
coverage, metadata/membership drift, finite aggregate overflow and conservation
at repeated/degenerate cuts.

## Architecture and operator contract

`patch_check_inputs.py` owns read-only directory membership captures and their
provenance. Existing `patch_dataset_artifacts.py` remains the owner of bounded
reference/geometry parsing. Pure radial helpers retain their call signatures and
validate complete populations. The STRIPMATCH builder's imported radial extent
function and the control recipes/tolerances remain in place.

The selection report's PASS concerns directory existence, nonempty positive
area, reference membership, bootstrap threshold and the existing 0.5 percentage-
point area tolerance. Spatial success is MEASURED with `balance_verdict:
not_assessed`. No new spatial balance gate was invented. Input failures use
FAIL/exit 1; parser errors use exit 2. Reports go to stdout, with no dataset
publication. Both paths remain stdlib-only and do not initialize ML runtimes.

Reference bytes and resolved membership mappings are captured and rechecked.
Spatial reports also verify geometry bytes and record an aggregate fingerprint.
Payload contents and immutable study lineage are unverified. Stable inputs are
still required; these checks are snapshots rather than locks. The guide explains
the reference/own-area denominators and repeated-cut interpretation. Historical
scientific measurements and preregistrations have not been restated.

## Verification

Commands from `/tmp`, with cached dependencies:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python /workspace/vesuvius-check-review/scripts/run_validation_tests.py --match '*patch_dataset_artifacts*' --match '*patch_input_checks*' --match '*build_stripmatch_dataset*' --match '*check_patch_selection*' --match '*check_patch_spatial_balance*' --match '*validation_runner*' --match '*validation_suite_covers_the_loop*' --match '*file_modes*' -- -rs
```

Captured: **8/150 curated modules; CUDA hidden; 146 passed in 20.30s**. This
includes the new input-check regressions, existing dataset publication/selection
and radial-conservation cases, the STRIPMATCH selector and validation-suite
guards, including the current-main dataset-mode regression and file-mode guard. Real CLI subprocesses run from an unrelated directory and parse one
JSON report, checking both successful and failed exit/status combinations.

From `/workspace/vesuvius-check-review`:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
/tmp/vesuvius-pr256-lint/bin/ruff check scripts/check_patch_selection.py scripts/check_patch_spatial_balance.py scripts/patch_check_inputs.py scripts/run_validation_tests.py tests/test_patch_input_checks.py
/tmp/vesuvius-pr256-lint/bin/ruff format --check scripts/check_patch_selection.py scripts/check_patch_spatial_balance.py scripts/patch_check_inputs.py scripts/run_validation_tests.py tests/test_patch_input_checks.py
PYTHONPATH=/tmp/vesuvius-pr256-types python3 -m mypy --follow-imports=skip --explicit-package-bases --namespace-packages --cache-dir /tmp/vesuvius-check-mypy scripts/check_patch_selection.py scripts/check_patch_spatial_balance.py scripts/patch_check_inputs.py scripts/run_validation_tests.py tests/test_patch_input_checks.py
git diff --check
```

Smoke: **8/11 passed, 3 skipped, 0 failed in 18.6s**. Two dataloader checks lack
local training data; optional bg2 augmentation is unavailable. Matplotlib/
fontconfig emitted cache-directory warnings. Ruff check/format passed, scoped
mypy found no issues in five files, and whitespace checks passed.

## Limits

No complete curated-suite run, production-size corpus, GPU inference, scientific
endpoint or active research-host integration was tested. These reports do not
establish readable payloads beyond directory existence, correctness of reference
fractions/areas, complete training history, statistical power, physical winding
calibration or prize eligibility. Radial spreading remains a descriptive proxy.
