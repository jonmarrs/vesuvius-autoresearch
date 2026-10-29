# Design and architecture review: NML ground-truth import

Baseline: `4d3db3cf` (after PR #293). Scope: the fiber benchmark's NML graph
loader, source identity, import policy and operator documentation. Work used an
isolated checkout, synthetic inputs and cached public annotations, without
accessing the active study's measurements or changing its runtime.

## Findings and fixes

| Priority | Verified defect | Change |
|---|---|---|
| P1 | Regex parsing silently dropped nodes, edges or entire trees when valid XML changed attribute order, quotes, coordinate formatting or empty-element syntax. Commented-out markup could create extra graphs. | Use the standard XML parser; preserve fractional coordinates, document order, namespaces and decoded names. |
| P1 | Malformed XML, invalid coordinates, duplicate IDs and incompatible origin vectors could yield incomplete or ambiguous ground truth. | Reject these inputs with source/field context; validate finite geometry, IDs and scale. Preserve valid empty/degenerate graph behavior. |
| P1 | A report rehashed the NML path after scoring. Replacing the annotation during scoring bound the new file's hash to the old graph's scores. | Capture bytes once, parse and hash those bytes, retain the hash through cube filtering and use it in benchmark reports. |
| P2 | The reader silently discarded edges referencing missing nodes. | Retain the legacy default graph, emit a count warning, and add `strict_edges=True` / benchmark `--strict-nml` to refuse partial graphs. |
| P2 | Provenance could not distinguish reader versions or dangling-edge policies when carrying old tracer rows into refreshed floors. | Add `skeleton_parser` version/policy to provenance, so mismatched and legacy rows are not carried forward. |
| P2 | The guide called version 4 current and described its covered-length denominator, although execution uses version 5. | Describe the current ground-truth-length denominator and the retained covered-length diagnostic fields. No metric formula changes. |

The first baseline regression run had **35 failures and 1 pass**, including
checks for the new strict API. A separate regression using the baseline
benchmark body reproduced the NML hash/score mismatch after a source rewrite.

## Architecture and compatibility

The XML reader is confined to `fibers/skeleton_io.py`; no new dependency or
training/inference framework was added. `Skeleton.source_sha256` identifies
the NML bytes parsed (or is `None` for a manually constructed graph). Cube
filtering retains that identity. `NML_PARSER_VERSION = 2` is distinct from
unchanged `SCORING_VERSION = 5`.

Node IDs and edge indices retain int64 storage, and coordinates retain float64.
Node and edge order remain the input document's order; this matters for branch
walks. Zero-length edges and out-of-bounds nodes are preserved. Missing-endpoint
edges retain the prior drop rule by default, with a warning instead of silence.
Strict mode refuses them before semantic inference or report replacement in
all three benchmark commands. Published results and registrations are unchanged.

## Verification

The commands below used `MPLCONFIGDIR=/tmp/vesuvius-nml-mpl`,
`XDG_CACHE_HOME=/tmp/vesuvius-nml-cache`, `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and `CUDA_VISIBLE_DEVICES=''`.

```sh
/tmp/vesuvius-chain-env/bin/python -m pytest -q -rs tests/test_nml_import_contracts.py tests/test_fiber_skeleton_io.py tests/test_fiber_workflow_contracts.py tests/test_fiber_eval_trace.py tests/test_fiber_trace.py tests/test_field_quality.py tests/test_tracing_context.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_validation_suite_covers_the_loop.py
```

**249 passed, 17 skipped, 7 warnings in 38.80s.** Tests cover equivalent XML
serializations and their connectivity scores, fractional geometry, duplicate
IDs, invalid metadata, dangling edges, strict CLI behavior, source mutation,
parser/policy changes during floor refresh, tracing and registry coverage.
The skips are four unavailable semantic-volume checks and thirteen comparisons
requiring a sibling ScrollGT checkout. Warnings are expected dangling edges in
the existing synthetic reader fixture. Both reader test modules are registered
in the curated suite.

```sh
PYTHONPATH=src /tmp/vesuvius-chain-env/bin/python /tmp/vesuvius-nml-corpus-parity.py
```

The local audit compared the baseline parser, the new strict parser and copies
reserialized with every attribute order reversed and explicit closing tags.
All **21 cached public NMLs** from the October 27 annotation audit match exactly:
**8,491 nonempty fibers, 467,440 nodes and 458,949 edges**, including IDs, names,
coordinates, edges, dtypes and frame metadata. All 21 reordered copies match
too. Source-file hashes remain unchanged and match the captured parser hashes.
The cached files are under `/workspace/shared/scrollgt-nml-provenance-2026-10-27/nml`;
the scratch audit script and those cached inputs are not checkout fixtures.
This is graph-import parity, not a new real-cube score or accuracy measurement.

```sh
/tmp/vesuvius-chain-env/bin/python scripts/smoke_test.py
```

**8/11 passed, 3 skipped, 0 failed in 19.1s.** Two training URI/inklabel fixtures
and the batchgeneratorsv2 transform are unavailable.

Ruff check and format-check pass on all four changed Python files. Targeted
Mypy with `--follow-imports=silent --explicit-package-bases --namespace-packages`
reports no issues in those files. `git diff --check` passes.

## Limits

This is not an NML schema validator or a check of annotation accuracy, units or
completeness. The NML hash does not make the whole benchmark immutable: model,
instance, image and cache inputs still require stable paths. NML bytes and XML
are held in memory while parsing. No GPU work, live-study inspection, deployment,
current online annotation refresh, real-volume scoring, prize submission or full
repository test run was performed. The separate ScrollGT repository and the
vendored scientific scorer were not modified.
