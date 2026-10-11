# Design and architecture review — relative sheet graphs

Date: 2026-10-11. Baseline: c1137bd7bedf1b9d54bc620de96be3f274c33728.
Scope: relative-angle estimation, graph input/output contracts, and the
legacy Thaumato solver sweep. This is a code and operator-flow review with
synthetic graph checks, not a new scroll experiment.

## What changed

Replaced ambiguous graph-solving output with bounded, reproducible relative-angle
diagnostics, corrected maximum-product paths, and retired the unsupported
Thaumato sweep and PKL adapter.

## Why

The previous estimator could select a weaker path, invent disconnected-node
angles, or produce dummy results for a missing input; the physical integration
and winding-correctness claims were unsupported.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | Missing CLI input substituted a dummy graph and reported success; existing output could be overwritten. | Require a real, bounded JSON source, publish only a new complete bundle, and return nonzero on invalid input or publication failure. |
| P1 | The PKL adapter treated the vendored graph as adjacency, guessed fields/units and wrote an absent node-angle member. | Reject PKL/bin conversion explicitly. Require a schema with declared angle units; leave any physical conversion to a separately verified integration. |
| P1 | The sweep could reuse old mesh output and rank texture variance as winding/legibility evidence; missing prerequisites returned success. Strategy and sprint text claimed solved physical stitching. | Retire the sweep with a nonzero, explanatory entry point that launches no producers; correct current support claims and qualify the historical coverage snapshot. |
| P2 | Maximum-product traversal finalized nodes at first discovery, retaining a weak direct edge over a stronger indirect path. | Relax routes and finalize on heap pop using Dijkstra on negative log confidence factors. |
| P2 | Heap ties compared heterogeneous IDs; set iteration and the global RNG made results unstable. | Canonical typed-ID order, independent heap ranks, sorted adjacency and a seeded local NumPy generator. |
| P2 | Random walks invented zero for unreachable nodes and treated zero-confidence edges as usable. | Exclude disabled edges, keep unreachable angles null, and label maximum-product fallback for reachable unsampled nodes. |
| P2 | Schemas, numeric values, budgets, reference node and arithmetic were unchecked; plain angle output hid conflicts and source identity. | Strict validation, bounded source/graph/walk work, finite arithmetic, explicit anchor/units/recipe, reachability, residuals and exact source-byte provenance. |

For the reproduced triangle, the direct route from s to b had factor 0.1 and
delta 99. The route s → a → b had factor 0.9 × 0.9 = 0.81 and delta 2. The old
code returned 99; the repaired estimator returns 2. The canonical b → s edge
has residual +97, so the report explicitly records inconsistent reachable
constraints. An isolated fourth node has a null angle.

The vendored source in
[instances_to_graph.py](../villa/deprecated/thaumato-anakalyptor/ThaumatoAnakalyptor/instances_to_graph.py)
defines node-pair edges with multiple sheet_offset_k variants, unbounded
certainty factors, and separate assigned_k/winding_angle degree conventions.
That format cannot be treated as this tool's single-edge confidence/delta
schema. No guessed conversion or solved-graph export remains.

## Architecture and operator flow

[The core](../scripts/sheet_graph.py) owns the graph contract, path estimator,
walk estimator and report semantics. [The CLI](../scripts/sheet_stitcher.py)
owns parsing, bounded source capture, recipe arguments and publication. It
reuses the existing finite-JSON writer, source fingerprints and new-directory
publisher. No new dependency or generic workflow framework was added.

The explicit schema separates typed node IDs, confidence factors and unwrapped
angle deltas. A fixed reference defines a relative gauge, not CT registration.
Reports expose selected paths, disabled/unreachable edges and constraint
residuals rather than claiming the graph is physically solved. Walk sample
counts and lower-order IQR are descriptive; correlated visits and inconsistent
cycles do not establish uncertainty or guaranteed outlier rejection.

A published bundle contains exact captured source bytes and finite estimates
with source path/stat signature/byte count/SHA-256, source-copy hash, limits,
units, anchor and actual settings. Both artifacts are staged and read back;
source bytes and identity are rechecked before publication. Existing output,
aliases, source changes and failed writes preserve prior artifacts.

[The operator guide](SHEET_GRAPH_DIAGNOSTICS.md) covers the schema, examples,
status interpretation, bounds, exit behavior and migration. The legacy
algorithm/function names remain aliases for the corrected path diagnostic;
unsupported PKL/bin output and the sweep fail explicitly. Strategy and sprint
claims now describe this scope. The coverage report retains its historical
rows/counts and explicitly qualifies their path-presence meaning.

## Verification

Commands below ran from the repository root using its existing environment.
No research loop, training, native solver or full-scroll pipeline was launched.

### Reproduce before repairing

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_sheet_graph_contracts.py -q --no-header --tb=short
~~~

Initial captured result:

~~~text
12 failed in 7.19s
~~~

Interpretation: the initial regressions reproduced weak-route selection, mixed
ID ties, fabricated unreachable angles, invalid anchors/confidence/endpoints,
dummy missing-input results, overwriting output and false prerequisite success.

### Focused graph contracts after repairing

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_sheet_graph_contracts.py -q --no-header --tb=short
~~~

~~~text
126 passed in 9.01s
~~~

Interpretation: graph arithmetic agrees with an exhaustive simple-path oracle;
typed IDs, deterministic order/seed, reachability, bounds, finite output,
provenance, CLI behavior and publication failure handling pass regression checks.

### Standard validation

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
~~~

~~~text
1595 passed, 3 skipped, 1 xfailed, 9 warnings in 218.24s (0:03:38)
~~~

Interpretation: the standard validation suite, including the new graph contracts,
passes. Warnings concern CPU-only checkpoint checks requesting pinned memory.

### Smoke checks

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
~~~

~~~text
8/11 passed, 3 skipped, 0 failed in 9.4s
~~~

Interpretation: available smoke paths pass, including 288/288 checkpoint keys.
Two paths lack optional local data and one lacks the optional bg2 dependency.

### Documentation and frozen-evidence guards

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py tests/test_tracer_rescore_numbers.py tests/test_tracer_frozen_numbers.py tests/test_villa_component_coverage.py -q --no-header --tb=short
~~~

~~~text
112 passed, 16 skipped in 23.87s
~~~

Interpretation: current documentation/coverage changes preserve frozen evidence
and historical counts; skips reflect unavailable optional fixtures.

After adding this report:

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
~~~

~~~text
16 passed in 5.23s
~~~

Interpretation: the completed operator guide and review report pass the document
reference and frozen-report claim checks.

### Static checks

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/sheet_graph.py scripts/sheet_stitcher.py scripts/autoresearch_thaumato_solver.py tests/test_sheet_graph_contracts.py scripts/run_validation_tests.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/sheet_graph.py scripts/sheet_stitcher.py scripts/autoresearch_thaumato_solver.py tests/test_sheet_graph_contracts.py scripts/run_validation_tests.py
git diff --check
~~~

~~~text
All checks passed!
5 files already formatted
~~~

Interpretation: changed Python files pass Ruff; whitespace checking emits no
diagnostics.

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
~~~

~~~text
Found 16 errors in 13 files (checked 634 source files)
~~~

Interpretation: repository-wide typing still reports the known baseline errors
in unchanged files (missing YAML/requests stubs, OpenCV overloads, augmentation
indices, optional loader tensors and training list/tensor operations). No
changed file has a mypy diagnostic.

### Representative CLI reports

Synthetic degree graphs were written under
/tmp/vesuvius-sheet-graph-review-25jxzyvc. Both have the triangle above and an
isolated node; the consistent graph uses delta 2 for the weak direct edge.

~~~sh
.venv/bin/python scripts/sheet_stitcher.py --input-graph /tmp/vesuvius-sheet-graph-review-25jxzyvc/consistent.json --out /tmp/vesuvius-sheet-graph-review-25jxzyvc/consistent --start-node '"s"' --algorithm max_product
.venv/bin/python scripts/sheet_stitcher.py --input-graph /tmp/vesuvius-sheet-graph-review-25jxzyvc/inconsistent.json --out /tmp/vesuvius-sheet-graph-review-25jxzyvc/inconsistent --start-node '"s"' --algorithm max_product
.venv/bin/python scripts/sheet_stitcher.py --input-graph /tmp/vesuvius-sheet-graph-review-25jxzyvc/inconsistent.json --out /tmp/vesuvius-sheet-graph-review-25jxzyvc/walk --start-node '"s"' --algorithm random_walk --walks 40 --walk-length 8 --seed 7
~~~

| Report | Status | Reachable / total | Violated / checked edges | Angle at b |
| --- | --- | --- | --- | --- |
| Consistent maximum-product | partial_reachability | 3 / 4 | 0 / 3 | 2 |
| Inconsistent maximum-product | inconsistent_reachable_constraints | 3 / 4 | 1 / 3 | 2 |
| Inconsistent seeded walk | inconsistent_reachable_constraints | 3 / 4 | 1 / 3 | 2 |

All three exited zero with their diagnostic status, retained a null isolated-node
angle, and had source-copy byte counts/SHA-256 independently checked against
the report. Interpretation: CLI output separates successful report generation
from complete reachability or constraint consistency.

## Edge cases considered

- Mixed integer/string IDs, equal path priorities, reversed edges, insertion
  order, multi-turn deltas and explicit nonzero references.
- Zero-weight edges, disconnected components, isolated anchors and reachable
  nodes unsampled by short walks.
- Subnormal confidence factors, overflowing angle/residual/IQR arithmetic,
  global RNG preservation and bounded walk counts/length/product.
- Invalid records, unknown keys, duplicate JSON keys/IDs/edges, booleans,
  numeric strings, nonfinite numbers, undeclared endpoints and invalid units.
- Oversized/deep/non-UTF-8 JSON, missing/nonregular/symlink/legacy sources,
  existing and aliased outputs, changed sources including preserved metadata,
  failed source-copy/JSON readback and an appearing destination.
- Actual CLI use outside the checkout, unused walk flags and retired sweep
  behavior without producers, history or dummy results.

## What was NOT tested

- Native Thaumato, Docker/GPU execution, real PKL/bin conversion, production
  graphs, mesh generation, CT rendering or full-scroll reconstruction.
- Absolute registration, winding ground truth, ink legibility, calibrated
  confidence/uncertainty or prize eligibility. Synthetic graph arithmetic
  validates the stated relative diagnostic contract only.
- Adversarial filesystem snapshots or concurrent publishers. Keep local sources
  stable and serialize writers; the existing publisher is not a locking API.
- Unrelated training/type-check defects identified by the established mypy
  baseline; training and evaluation harness behavior were outside this review.

## Reviewer focus

Scrutinize the explicit units/edge orientation, reachable-only angle semantics,
strongest-path relaxation and conflict diagnostics, plus the retirement of
unsupported physical integration and its claims.
