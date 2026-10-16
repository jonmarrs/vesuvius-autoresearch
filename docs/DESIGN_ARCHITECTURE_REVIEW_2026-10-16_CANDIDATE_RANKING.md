# Design and architecture review — candidate-ranking boundaries

Date: 2026-10-16. Baseline: `37fb893744e46061bff2e169591053ff469d9657`
(main after PR #88).

The original results below use that baseline. The [PR #90 review](#pr-90-review)
records integration with main after PR #89 and the additional review fixes.

## What changed

Candidate ranking validates prediction provenance, completeness and probability
arrays before assigning bonuses. It recomputes statistics from validated arrays,
keeps corrupt optional artifacts from aborting healthy rows, and rejects invalid
queue priorities before publishing a ranked TSV.

## Why

The inference producer validates geometry and writes completion metadata, but
the ranking consumer used only a coordinate-based filename and an ink-recipe
string. That lost the producer's guarantees at the next boundary. Ranker output
then flows into the Lasagna/fiber worklist, where both ink statistics and fiber
mean influence priority even outside the ranker's own prediction bonus.

## Findings and repairs

| Priority | Verified problem | Repair |
| --- | --- | --- |
| P2 | A prediction from another scroll at the same coordinates earns a bonus. Wrong geometry, calibration and incomplete runs also pass. | Bind the sidecar to the queue source, position, dimensions, patch size and voxel size; require complete, unsharded coverage with all recorded tiles processed. |
| P2 | Truncated NPY files abort the entire queue; wrong shapes, nonfinite values, integers and values outside the probability range can enter scoring. Stored metadata summaries overwrite the actual ink-map statistics. | Read arrays without pickle, using read-only memory mapping; validate shape, floating dtype, finite values and range before reducing. Use array statistics directly and report per-row failures. |
| P2 | A retained fiber map receives a downstream bonus even when the ink map is missing; a corrupt fiber map aborts ranking. | Read fiber only after valid matching ink, and only when the sidecar records fiber statistics. A bad optional fiber map contributes zero fiber signal and leaves valid ink usable. |
| P2 | Malformed CT chunk dimensions raise indexing or division errors outside the old JSON error handler. | Validate three positive integer chunk dimensions and the separator; report unknown occupancy plus a diagnostic on failure. |
| P2 | NaN/infinite priorities produce nonfinite scores, and a nonnumeric priority silently becomes the default. | Require finite numeric priorities before writing a ranked output. |

## Architecture assessment

- The existing shared inference helpers, strict weight loading, model-head
  declarations and metadata-last publication provide useful producer boundaries.
  The repair belongs in ranking, where files become evidence for another source.
- Source identity, geometry and completeness are checked before opening NPY maps.
  Numerical validation is shared by ink and fiber. One bad optional artifact is
  isolated to its candidate rather than stopping unrelated rows.
- Ranking remains a CPU metadata/statistics command using NumPy and the existing
  lightweight recipe constant. It imports neither Torch nor the inference
  producer. The existing subprocess check covers this separation.
- Artifact problems yield explicit TSV diagnostics. Invalid queue geometry or
  priorities remain input errors: publication stops instead of fabricating a
  different candidate or emitting nonfinite scores.
- The review traced the CT-input, inference-export, ranking and fiber-worklist
  handoffs. It did not change training, evaluation metrics, promotion decisions,
  checkpoints, loop state, preregistrations or the Villa pin.

## Verification

The environment has no project virtualenv or full Villa checkout. Commands use
the cached Python 3.10 interpreter and package archives through the unchanged
bootstrap documented in [the previous review report](PR88_REVIEW_FIXES_2026-10-16.md#runtime-bootstrap).
The pinned structure-tensor source is supplied externally for inference tests.
No packages were installed. Baseline runs use a detached clean worktree at the
reviewed commit; fix runs use this branch.

### Failure reproduction

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py -m pytest -q tests/test_candidate_ranking_contracts.py --no-header --tb=short
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py -m pytest -q tests/test_candidate_ranking_contracts.py -k invalid_queue_priority --no-header --tb=short
```

```text
Before the artifact-boundary fixes: 30 failed, 1 warning in 0.39s
Before the priority fix:             4 failed, 30 deselected in 0.15s
```

Interpretation: all 34 new cases reproduce failures before their corresponding
fixes. Happy-path fixtures now include the producer's actual metadata contract;
the regional inference tests also pass real writer output into ranking.

### Affected workflows

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py -m pytest -q tests/test_candidate_ranking_contracts.py tests/test_prize_readiness.py tests/test_volume_inference_contracts.py tests/test_submission_contracts.py tests/test_production_predict.py tests/test_lasagna_fiber_worklist.py tests/test_candidate_fiber_report_contracts.py --no-header --tb=short
```

```text
376 passed in 19.26s
```

Interpretation: the first focused run passed across producers and downstream
consumers. Four priority regression cases were added afterward; the final
standard-suite JUnit report below confirms all 380 affected cases passed.

### Standard-suite comparison

The runner uses the existing `run_validation_tests.VALIDATION_TESTS`, with
`--continue-on-collection-errors -rfE --tb=short` and JUnit output. The new
regression module is registered in this list. Baseline command first, from the
clean baseline worktree, then fixes from this branch:

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-run-standard.py /tmp/ranking-review-baseline.xml
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-run-standard.py /tmp/ranking-review-final.xml
python3 /tmp/ranking-review-compare.py
```

```text
Baseline: 104 failed, 2170 passed, 18 skipped, 1 xfailed, 3 warnings, 1 error in 176.22s
Fixes:    104 failed, 2204 passed, 18 skipped, 1 xfailed, 3 warnings, 1 error in 175.88s
Baseline failure/error IDs: 105
Final failure/error IDs: 105
New failure/error IDs: []
Resolved failure/error IDs: []
Additional passing cases: 34
Final affected-module results: {'passed': 380}
```

The comparison parses `(classname, name)` from JUnit XML and asserts identical
failure/error sets, exactly 34 additional passing cases and 380 passing cases
across the seven affected modules. Interpretation: no additional failures in
this environment. The full suite remains red. Unavailable Villa Tifxyz, sampling,
curation and metric code, missing native dependencies and external artifacts
remain unverified; `test_dice.py` cannot import `metrics` during collection.

### Smoke

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py scripts/smoke_test.py
```

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
SKIP: augmentations_bg2 — create_training_transforms not available
--- 8/11 passed, 3 skipped, 0 failed in 5.3s ---
```

Interpretation: available smoke paths pass and the incumbent loads completely;
three unavailable data/backend paths remain unverified.

### Documentation and source checks

The wrapper runs the nine documentation guards listed in
`.pre-commit-config.yaml`; its source is recorded in the previous review report.
Baseline command first, then this branch:

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-fix-doc-tests.py /tmp/ranking-review-baseline-docs.xml
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-fix-doc-tests.py /tmp/ranking-review-final-docs.xml
```

```text
Baseline: 1 failed, 90 passed, 2 skipped in 12.35s
Fixes:    1 failed, 90 passed, 2 skipped in 12.15s
FAILED tests/test_audit_doc_references.py::test_live_documents_stay_clean
Missing-path diagnostics match baseline exactly.
```

Interpretation: the same reference guard fails for the same absent Villa files
and external detector weights. No new reference failure was introduced.

`git diff --check` passes. All five changed Python files compile, and all eight
changed files pass manual whitespace, final-newline and 2 MiB size checks. Ruff
and mypy executables and cached modules are absent, so lint/type checking remains
unverified. Protected artifacts and the Villa pin match the reviewed commit.

## Edge cases considered

- Different sources sharing the same coordinate basename cannot share bonuses.
- Missing or incomplete provenance receives no prediction or fiber bonus.
- Invalid ink contributes no statistics; invalid optional fiber preserves usable
  ink, with a separate map diagnostic.
- Bad CT metadata remains unknown rather than pretending a chunk is absent.
- Old QC-gated recipes remain ineligible; headless reruns ignore retained fiber.
- The ranking command still avoids importing Torch.

## What was NOT tested

- CUDA, real scroll data or scientific accuracy; these are artifact contracts,
  not a new measurement of ink detection or fiber validity.
- Ruff and mypy are unavailable in this environment; no packages were installed.
- Concurrent writers, source mutation during ranking, cryptographic binding of
  arrays to sidecars, or recovery of predictions overwritten by basename
  collisions. Use separate output directories for separate sources.
- Full CT payload coverage: occupancy still checks one center chunk only.
- Atomic or durable replacement of a ranked TSV after filesystem write failure.

## Reviewer focus

Check that no bonus escapes a failed identity/numerical validation, that retained
fiber cannot survive missing ink, and that per-row diagnostics preserve healthy
candidates without changing scientific claims.

## PR #90 review

Reviewed published head `f2beb3eb9787f6495a3467f329ac0591fc698884` against
main `8e2d4b9a7c83caa3c337e915808211bb5773f63e` (after PR #89), with the
evidence-chain changes integrated before review.

| Finding | Repair and coverage |
| --- | --- |
| Missing queue coordinates defaulted to zero; a region smaller than its model patch was ranked even though inference would reject it. | Require every coordinate and at least one patch in each spatial dimension. Missing-coordinate cases preserve a previous TSV instead of overwriting it. The old custom-sidecar test now records its actual 8 px patch for its 13×11 region. |
| Malformed source metadata escaped the per-row error boundary: a huge integer voxel size raised `OverflowError`, and `Path.resolve()` on a cyclic symlink raised `RuntimeError`. | Catch numeric overflow as an artifact error and translate path-resolution failures into invalid source metadata. Both cases yield zero prediction/fiber bonuses with diagnostics. Equivalent relative and absolute local source paths remain accepted. |

### Review reproductions

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py -m pytest -q tests/test_candidate_ranking_contracts.py -k 'missing_queue_coordinates or smaller_than_a_model_patch or oversized_metadata_number or unresolvable_metadata_source or equivalent_local_source_paths' --no-header --tb=short
```

```text
Before review fixes: 7 failed, 1 passed, 34 deselected in 0.25s
```

Interpretation: seven new cases reproduce the two review findings; one positive
case protects valid local source-path normalization.

### Integrated workflow verification

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py -m pytest -q tests/test_candidate_ranking_contracts.py tests/test_prize_readiness.py tests/test_volume_inference_contracts.py tests/test_submission_contracts.py tests/test_production_predict.py tests/test_lasagna_fiber_worklist.py tests/test_candidate_fiber_report_contracts.py --no-header --tb=short
```

```text
404 passed in 19.87s
```

Interpretation: all affected cases pass with main after PR #89 and the review
fixes, including all 42 candidate-ranking cases. The original 34 plus seven new
cases failed before their respective fixes; the extra normalization case passed
before and after. The original environment limitations still apply.

### Full comparison against the PR base

Baseline command runs from a clean detached worktree at `8e2d4b9a`; final
command runs from the reviewed branch, using the same cached environment.

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-run-standard.py /tmp/pr90-baseline.xml
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-run-standard.py /tmp/pr90-final.xml
python3 /tmp/pr90-compare.py
```

```text
Baseline: 104 failed, 2186 passed, 18 skipped, 1 xfailed, 3 warnings, 1 error in 185.82s
Final:    104 failed, 2228 passed, 18 skipped, 1 xfailed, 3 warnings, 1 error in 174.92s
Baseline failure/error IDs: 105
Final failure/error IDs: 105
New failure/error IDs: []
Resolved failure/error IDs: []
Additional passing cases: 42
Final affected-module results: {'passed': 404}
```

Interpretation: comparison by JUnit case identity confirms no new failure/error
IDs relative to the current PR base, all 42 additional cases passing and all
404 affected cases passing. The full suite still has the documented baseline
failures and collection error; it is not a clean integration certification.

### Final smoke

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py scripts/smoke_test.py
```

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
--- 8/11 passed, 3 skipped, 0 failed in 5.4s ---
```

Interpretation: the available smoke paths still pass after review; the same
missing-data and backend skips remain.

### Final documentation and static checks

Baseline command uses the clean PR-base worktree; final command uses this branch.

```sh
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-fix-doc-tests.py /tmp/pr90-baseline-docs.xml
VESUVIUS_REVIEW_VILLA_SOURCE=/tmp/vesuvius-pr88-review-ejvgzkfp/villa/vesuvius/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/pr88-matplotlib /workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 /tmp/pr88-run-python.py /tmp/pr88-fix-doc-tests.py /tmp/pr90-final-docs.xml
```

```text
Baseline: 1 failed, 90 passed, 2 skipped in 11.83s
Final:    1 failed, 90 passed, 2 skipped in 11.66s
Documentation failure IDs and missing-path diagnostics match the PR base exactly.
```

Interpretation: the same reference failure for unavailable Villa files and
external detector weights remains; there are no new reference diagnostics.
Python syntax, whitespace, final-newline, file-size and `git diff --check`
checks pass. Ruff/mypy remain unavailable. Protected artifacts and the Villa pin
match the PR base.
