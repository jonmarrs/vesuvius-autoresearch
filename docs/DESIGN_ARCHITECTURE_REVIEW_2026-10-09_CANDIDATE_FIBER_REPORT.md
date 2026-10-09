# Design and architecture review: candidate ink/fiber reporting

Reviewed baseline `3a245f12` after the merged spatial-inspection review. This pass
covers the existing-artifact report in `scripts/cross_scroll_validation.py`:
input design, geometry and encoding contracts, descriptive metrics, candidate
failure handling, provenance, selection, and publication. It does not change
training, model evaluation, label-generation algorithms, or historical studies.

## What changed

Make candidate ink/fiber reporting bounded and explicit, preserve failures and
undefined metrics, and publish one verified JSON/Markdown report directory.

## Why

The previous report silently cropped mismatches, truncated volumetric ink,
misread binary fiber encodings, wrote nonfinite JSON, overwrote sources, and
claimed independent consistency validation without checked fiber registration.

## Findings and repairs

| Priority | Verified problem | Repair |
|---|---|---|
| P1 | Shape mismatch is cropped to the common upper-left rectangle; 3D ink uses only its first slice. Neither establishes alignment. | Require exact candidate/ink/fiber YX agreement, accept only a surface ink map, reject contradictory recorded prediction source/origin/dimensions, and keep fiber alignment unverified. |
| P1 | Arbitrary nonfinite/out-of-range probabilities and threshold values are accepted, and 0/255 fiber labels yield occupancy above one. | Validate finite probabilities and numeric parameters, normalize binary fiber encodings, reject ambiguous TIFF/channel layouts and multiclass values, and enforce read budgets before decompression. |
| P1 | A zero fiber-region ink mean produces Infinity in JSON; undefined ratios are omitted from averages without denominator counts. | Keep undefined ratios null with reasons, report actual ratio denominators/reason counts, and label equal-weight candidate aggregation separately from pixel pooling. |
| P1 | JSON/Markdown are written directly and independently; either destination can overwrite candidate metadata and a failed second write leaves half a report. | Require one new source-disjoint directory, stage and verify both outputs, preserve prior files, and reject changes before publication. Retire the file-pair flags. |
| P2 | Malformed metadata can crash the entire report; corrupt reads look like missing files; zero successful candidates still exits zero. | Preserve candidate-specific missing/invalid statuses, catch ordinary read/metadata failures, exclude failures from aggregation, and return exit 2 for an explicit partial report. |
| P2 | Auto-generation invokes an absent script, ignores the selected evidence root, and generates only top N while the report reads every directory lexicographically. | Retire producer execution from reporting; select the first N numeric indices with explicit count budgets and expose requested/discovered/selected/inspected/failed counts. |
| P2 | The report calls the CT-derived fiber signal independent and interprets ratios as correct/inconsistent ink behavior. | Present descriptive array co-occurrence only; never infer registration, accuracy, independent validation, generalization, or eligibility from these artifacts. |

The initial regression command was:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_candidate_fiber_report_contracts.py -q --no-header --tb=short
```

Captured: **15 failed in 2.38s**. It reproduced silent alignment/truncation,
numeric/encoding failures, nonfinite ratios, metadata crashes, false-success
exit behavior, and source overwrite. Those cases pass after the repairs.

## Architecture decisions

Keep inspection separate from preparation and model execution. Reuse existing
numeric, level-zero array, aligned-plane, finite JSON, file-hash, and immutable
publication helpers. Stream one bounded candidate at a time; retain scalar
records rather than all arrays. Read real producer metadata when available,
refuse contradictions, and distinguish recorded prediction facts from missing
fiber-origin evidence. The real exporter is exercised without running a model.

The operator contract and intentional CLI migration are in
[Candidate ink/fiber reports](CANDIDATE_INK_FIBER_REPORTS.md). The historical Python
filename remains for discoverability, while generated titles and JSON scope
state the current descriptive behavior.

## Verification

Focused regressions:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_candidate_fiber_report_contracts.py -q --no-header --tb=short
```

Captured: **111 passed in 15.79s**. Numeric and artifact contracts, actual exporter
roundtrips, candidate selection, finite ratios, mixed failures, outside-checkout
CLI behavior, immutable paired publication, and source-change rollback pass.
The actual generated Markdown was also read to check its values, ratio
denominators, candidate statuses, and descriptive scope.

Standard validation:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
```

Captured: **1261 passed, 3 skipped, 1 xfailed, 9 warnings in 233.69s (0:03:53)**.
The standard workflow suite, including all 111 new candidate-report regressions,
passes. Existing optional checks and the upstream expected failure retain their
conditions; warnings concern data-loader pinning on CPU.

Required smoke:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
```

Captured: **8/11 passed, 3 skipped, 0 failed in 28.9s**. Imports, architectures and
auxiliary heads, actual best-checkpoint loading (288/288 keys), augmentations,
and bandit templates pass. Two absent local-data fixtures and the unavailable
optional `batchgeneratorsv2` transform account for skips.

Documentation, claim, filing-number, and upstream-parity guards:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py -q --no-header --tb=short
```

Captured: **106 passed, 16 skipped in 32.04s**. Available reference/claim guards
pass. Skips require a missing sibling ScrollGT checkout or external render
artifacts; historical results were not rerun or regenerated.

Final reference/claim check after completing the report:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
```

Captured: **16 passed in 8.24s**. The completed documentation's references and
claim guards pass.

Typing:

```bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
```

Captured: **Found 16 errors in 13 files (checked 624 source files)**. This remains
a failing check with the same baseline diagnostics: missing YAML/requests stubs,
OpenCV overloads, augmentation slice types, loader tensor-list annotations, and
training tensor-list mean/variance calls. None are in changed files.

Lint, format, and whitespace:

```bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/cross_scroll_validation.py scripts/run_validation_tests.py tests/test_candidate_fiber_report_contracts.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/cross_scroll_validation.py scripts/run_validation_tests.py tests/test_candidate_fiber_report_contracts.py
git diff --check
```

Captured: **All checks passed!**, **3 files already formatted**, and no whitespace
diagnostics. Cached lint/typing tools ran offline; no dependency or upstream
source changes were needed.

## Edge cases considered

Shape mismatch; empty, volumetric, wrong-dtype, nonfinite, and out-of-range ink;
0/1 versus 0/255 labels, mixed encodings, probabilistic/multiclass labels,
RGB/multiple-series TIFFs; strict threshold boundaries and sparse depth;
absent regions, zero denominators and ratio overflow; malformed/duplicate/nonfinite
JSON; invalid coordinate/dimension/basename/string fields; missing provenance,
conflicting origins/sources/dimensions and partial predictions; bounded reads and
corrupt actual chunks; numeric selection, duplicate/invalid/symlink directories;
mixed success/failure and actual aggregate denominators; existing/source/alias
outputs; corrupt and failed second writes; changing inputs/appearing metadata
or destination; escaped Markdown; and CLI invocation outside the checkout.

## What was NOT tested

GPU/model execution, full scrolls, physical fiber registration, causal ink/fiber
relationships, held-out lineage, independent validation, complete chunk/blend
coverage, raw-store/CT-byte hashing, historical experiment reruns, or prize
eligibility. Tests use local synthetic artifacts and the real artifact exporter;
they establish mechanics rather than scientific quality. Publication assumes
serialized writers and stable sources. Label generation remains a separate
workflow; the report invokes no producer.

## Reviewer focus

Review the exact surface/binary/shape contracts, absence-versus-invalid failure
statuses, ratio denominators, conditional prediction metadata checks, shape-only
alignment wording, and complete report publication. CLI migration is intentional.
