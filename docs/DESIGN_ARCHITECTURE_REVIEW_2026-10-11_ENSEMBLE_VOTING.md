# Design and architecture review — ensemble voting

Date: 2026-10-11. Baseline: 787aae32092ac36abc4a02400c956a8398c18842.
Scope: generic tensor voting, its relationship to regional probability
inference, and the legacy First Title launcher/operator claims. Verification
uses synthetic tensors and local temporary directories, not new scroll results.

## What changed

Hardened SwarmVoter into an explicit normalized weighted-mean module and replaced
the simulated First Title launcher with a nonzero unimplemented response.

## Why

Unnormalized weights could silently scale predictions, malformed/nonfinite
outputs could corrupt or lose heads, and simulated scans were reported as
completed searches with zero candidates.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | First Title search slept instead of invoking inference and printed zero candidates with exit zero, even for missing data. | Exit 1 with an explicit unimplemented message, launch no producer and report no scan/detection/absence result. |
| P2 | Weights [1, 3] produced a scaled sum instead of a weighted mean; empty, mismatched, all-zero, negative or nonfinite weights were accepted. | Validate 1..64 module members and one finite nonnegative relative weight per member, with a positive total; reject nonzero values/ratios that underflow float64 and normalize using rescaling before summation. |
| P2 | Caller-owned weights and a separate buffer could drift; checkpoint reloads did not update the public weight state. | Use the registered buffer as the sole state source; expose an immutable tuple of effective coefficients and revalidate before invocation. |
| P2 | Zero-weight members still ran and could fail or contaminate the result; first-member structure defined how all outputs were interpreted. | Skip disabled members entirely and infer structure from the first active member. |
| P2 | Extra tuple heads could be silently discarded, and integer/nonfinite or incompatible outputs lacked explicit validation. | Require matching tensor/flat-tuple structure, head counts and corresponding shape/dtype/device, with dense finite real tensors. |
| P2 | Half-precision weight/products rounded a constant uniform mean from 65,504 to 65,472, and all model tensors were stacked together. | Accumulate half/bfloat16 heads in float32 with streaming totals, preserve output dtype/device and reject nonfinite final arithmetic. |
| P2 | Sprint and historical submission wording claimed voting eliminated hallucinations and implied a completed title workflow. | Correct the support/evidence claims and link a guide distinguishing tensor averaging, regional predictions and unimplemented search. |

Two constant models outputting 1 and 3 with weights [1, 3] previously returned
10; the corrected normalized mean is 2.5. Three uniform half-precision models
outputting 65,504 previously returned 65,472; float32 accumulation returns
65,504 in the original output dtype. A second tuple member with three heads
after a two-head first member previously lost its third head silently.

The title launcher had no model load, volume read, inference, candidate
detector or artifact producer. Both branches of its path-existence check slept
and then printed a completed scan with zero candidates. Such a message cannot
establish that the region was scanned or that a title was absent.

## Architecture and operator flow

[SwarmVoter](../scripts/swarm_voter.py) remains a small PyTorch module:
weight normalization, head validation and streaming aggregation live together.
Its registered buffer is the only weight state, including after state reload
and dtype/device conversion. Constructor and forward checks prevent invalid
vectors or changed member counts from running models. Active model errors
propagate, and autograd flows through the actual normalized arithmetic.

The [regional ensemble CLI](../scripts/inference/ensemble_predict.py) has its
existing probability/QC/spatial-context contract. Generic voting averages raw
head tensors; it has no checkpoint loading, activations, gating, TTA, calibration
or evidence export. These distinct semantics are documented explicitly rather
than calling every average a validated ensemble decision. Shape/dtype/device
checks do not establish matching physical coordinates or output meaning.

[The title entry point](../scripts/search_first_title.py) is retained so existing
invocations receive a useful failure message. Legacy scroll and batch-size
options are accepted for that explanation only. Help describes the scope.
Execution produces no successful search claim, predictions, discovery images
or history, regardless of whether local directories exist.

[The guide](ENSEMBLE_VOTING.md) covers normalized weights, disabled members,
supported output structures/dtypes, arithmetic limits, state/autograd/mode
behavior, migration and actual regional prediction options. Current sprint
claims and the historical April draft's voting assertion are corrected with
an explicit scope note. No scientific result, training/evaluation harness or
native Villa code was changed, and no dependency was added.

## Verification

All commands ran from the repository root with the existing environment.
Process inspection found no active training, research loop or render/fit;
no experiment was launched for this review.

### Reproduce before repairing

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_ensemble_voting_contracts.py -q --no-header --tb=short
~~~

~~~text
15 failed in 6.49s
~~~

Interpretation: the initial regressions reproduced weight scaling/validation,
empty membership, caller-list mutation, disabled-member execution, discarded
tuple heads, nonfinite/integer outputs, half-precision rounding drift and
simulated search success.

### Focused voting contracts after repairing

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_ensemble_voting_contracts.py tests/test_swarm_voter.py -q --no-header --tb=short
~~~

~~~text
73 passed, 1 skipped in 4.01s
~~~

Interpretation: corrected numerical behavior, state reload, gradients, metadata
and malformed-output checks, kwargs, modes and actual retired-launcher subprocess
behavior pass. The CUDA test is skipped because this environment has no GPU.

The final conversion-boundary check also reproduced positive/negative real
weights underflowing to zero before the fix:

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_ensemble_voting_contracts.py -q --no-header --tb=short -k underflow_real
~~~

~~~text
2 failed, 71 deselected in 2.71s
~~~

Interpretation: both original-sign and float64 representability checks are
needed; these two regressions pass in the final focused suite above.

### Standard validation

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
~~~

~~~text
1668 passed, 4 skipped, 1 xfailed, 9 warnings in 260.40s (0:04:20)
~~~

Interpretation: the final code passes standard validation with voting contracts
included. One additional skip is the unavailable CUDA path; warnings concern
pinned-memory requests in CPU-only checkpoint checks.

### Smoke checks

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
~~~

~~~text
--- 8/11 passed, 3 skipped, 0 failed in 16.3s ---
~~~

Interpretation: available smoke paths pass, including 288/288 checkpoint keys.
Two optional local-data checks and the unavailable bg2 augmentation path skip.

### Documentation and frozen-evidence guards

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py tests/test_tracer_rescore_numbers.py tests/test_tracer_frozen_numbers.py tests/test_villa_component_coverage.py -q --no-header --tb=short
~~~

~~~text
112 passed, 16 skipped in 35.24s
~~~

Interpretation: current support-claim edits preserve frozen scientific evidence
and historical coverage counts; optional fixtures account for skips.

Final document-reference/report-claim check after adding this report:

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
~~~

~~~text
16 passed in 5.80s
~~~

Interpretation: the operator guide and review report pass path/reference and
frozen-report claim checks.

### Static checks

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/swarm_voter.py scripts/search_first_title.py scripts/run_validation_tests.py tests/test_ensemble_voting_contracts.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/swarm_voter.py scripts/search_first_title.py scripts/run_validation_tests.py tests/test_ensemble_voting_contracts.py
git diff --check
~~~

~~~text
All checks passed!
4 files already formatted
~~~

Interpretation: changed Python files pass Ruff; whitespace checks emit no
diagnostics.

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
~~~

~~~text
Found 16 errors in 13 files (checked 635 source files)
~~~

Interpretation: mypy retains the established errors in unchanged files (missing
YAML/requests stubs, OpenCV overloads, augmentation indices, optional loader
tensors and training list/tensor operations). No changed file has a diagnostic.


### Integration with updated main before PR creation

The branch was rebased onto 2a816bddf654f43fbdec378e2d8edadba7837790,
which adds an independent current-annotation analysis and frozen reports.
A comparison with the reviewed commit confirmed all nine review files were
unchanged by the rebase; the selected standard-validation test files and
shared runtime were also unchanged. The complete standard suite above ran
before that rebase. The updated documentation/evidence checks and new analysis
tests were then run together:

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py tests/test_tracer_rescore_numbers.py tests/test_tracer_frozen_numbers.py tests/test_villa_component_coverage.py tests/test_scrollgt_current_annotations_analysis.py tests/test_scrollgt_current_annotations_numbers.py -q --no-header --tb=short
~~~

~~~text
121 passed, 16 skipped in 36.26s
~~~

Interpretation: integrating the latest main preserves the reviewed changes and
passes the current reference, frozen-evidence and annotation-analysis checks.

Repeating the mypy command above after the rebase produced:

~~~text
Found 16 errors in 13 files (checked 638 source files)
~~~

Interpretation: the additional analysis files leave the same established typing
errors in unchanged files; no review file has a diagnostic.


## Edge cases considered

- Relative/large finite weights, disabled first/last members, all-zero or invalid
  vectors, positive/negative real values underflowing during conversion,
  unrepresentable positive ratios and mutation of caller-owned lists.
- Checkpoint weight reloads, legacy unnormalized buffers, invalid buffer rank,
  length, dtype, values, layout, device or trainability, and changed membership.
- Single tensors and tuples with differently shaped heads, incompatible per-head
  metadata, extra/empty/nested heads, scalar outputs, integer/bool/complex/sparse/
  meta/empty/nonfinite tensors.
- float16, bfloat16, float32 and float64 behavior; normalized autograd coefficients,
  disabled-member gradients, module dtype/mode changes, kwargs and producer errors.
- Actual title-launcher CLI calls outside the checkout with missing or present
  scroll directories, legacy options, help and preservation of prior predictions.

## What was NOT tested

- CUDA execution or performance: the focused GPU test skipped because no GPU is
  available. Float32/64 overflow is an explicit failure boundary, not a guarantee
  of arbitrary-precision arithmetic.
- TorchScript/export/compile, distributed voting, concurrent state mutation or
  a transactional state loader; this is an eager PyTorch module with fixed weights.
- Native Villa TTA execution or a production ensemble accuracy benchmark; matching
  tensor metadata alone does not establish compatible models or physical frames.
- Full-scroll/colophon search, title detection, legibility, ground-truth accuracy,
  calibrated uncertainty or prize eligibility. The legacy search is unimplemented.
- Training experiments or unrelated errors in the established mypy baseline.

## Reviewer focus

Review the normalized mean and disabled-member semantics, the buffer as the
single weight state, head validation/autograd/dtype behavior, and the removal
of simulated search and hallucination-elimination claims.
