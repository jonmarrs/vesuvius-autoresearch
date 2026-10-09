# Design and architecture review: pseudo-label handoff

Reviewed baseline `0ec18c0d`, after the merged checkpoint export review. This
pass covers 2D teacher-generated pseudo-label preparation, merging, scoring,
publication, and the actual training consumer. It does not rerun the research
study or change loss/model/evaluation mathematics.

## Findings and repairs

| Priority | Verified problem | Repair |
|---|---|---|
| P1 | The iterative driver prints completed training simulations, repeats an unchanged teacher, guesses scroll paths, and calls flags the actual producer does not support. | Require a recorded checkpoint and explicit region manifest. Default to a validated dry run; execute one real preparation batch with the actual CLI and interpreter. A published manifest states that no training ran. |
| P1 | `maximum(manual, pseudo)` overwrites known manual background and promotes ignore 128 over background. | Require an explicit manual-known mask and overwrite pseudo values with both known manual classes. Preserve ignore outside known/scored pixels. |
| P1 | Merged files use `_combined.png`, while the trainer looks for `_pseudo.png` and otherwise ignores the merged output. Manual-only segments disappear. | Match the actual consumer filename, retain the union of segment sources, reject duplicate manifest basenames/volumes, and test the real dataset handoff. |
| P1 | Producers and merges overwrite outputs directly, accept malformed label artifacts, and can leave incomplete batches. | Validate bounded single-channel PNG encodings and alignment, reject source aliases and existing outputs, stage individual files and whole batches, and publish only after all children and checks succeed. |
| P2 | All-ignore inputs and one-class truth receive fabricated chance AUC; undefined precision/recall are manufactured zeros. Region coverage uses pixels outside the requested region. | Validate scoring inputs, report unknown metrics as null/nonzero indeterminate CLI results, use the declared region denominator, and identify hard-label AUC explicitly. |
| P2 | The obsolete generator cannot even show help outside the checkout and has a separate architecture-guessing implementation. | Delegate its entry point to the strict region-mask producer; retire incompatible flags. |
| P2 | The real dataset imports Villa's entire optional ML package tree to access a standalone sampler, failing here on missing `nrrd`. | Lazily load the actual pinned sampler file. Preserve its implementation and call arguments; verify parity and a real producer run without installing dependencies. |
| P2 | Producer documentation claims ignore is weighted exactly zero. PNG 128 actually normalizes to 128/255 and receives weight 1/255. | Correct the operator contract and require confidence weighting for separate training. Verify the real loader and existing loss numerics; leave scientific formulas unchanged. |

The initial regression suite reproduced **8 failures** on the baseline. Their
observed output was `8 failed in 9.34s`: overwritten manual background, wrong
consumer filenames, discarded manual-only labels, acceptance of malformed
pseudo values, fabricated no-evidence and one-class AUC, existing PNG overwrite,
and broken legacy help. The repaired operator workflow is documented in
[Pseudo-label preparation](PSEUDO_LABEL_HANDOFF.md).

## Architecture decisions

Use shared label validators and the existing immutable artifact publishers,
checkpoint model factory, and process supervisor. Keep only one inference
implementation and the pinned upstream patch sampler. The preparation driver
owns orchestration and provenance; numerical merging and scoring validate their
own boundaries. Source CT is read by patch, while mosaics/masks are bounded by an
explicit pixel budget. No dependency or upstream source changes are needed.
Teacher generation does not read ambient fragment labels; manual input is
explicit at the merge boundary, and unused annotations cannot affect preparation.

A label-preparation manifest does not attest to retraining, held-out lineage,
accuracy, or eligibility. Supplied holdout overlap is checked, but exact ignore
mask enforcement remains absent from the existing training loss. This is an
explicit limitation rather than a claim of leakage prevention. Real subsequent
rounds require separately trained and recorded checkpoints.

## Verification

### Standard validation

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
```

```text
1070 passed, 3 skipped, 1 xfailed, 9 warnings in 115.81s (0:01:55)
```

The final standard suite passes, including all **62 new regression cases** and
the existing quality/loss checks added to the runner. It exercises real CPU
producer and training-dataset handoffs, whole-batch rollback after a later child
fails, and canonical source-volume write boundaries. The expected xfail remains
the previously documented pinned Mutex loader defect; no upstream source was
changed. Warnings concern CPU DataLoader pinning. Three optional/external checks
remain skipped.

### Focused producer and consumer checks

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_pseudo_handoff_contracts.py tests/test_pseudo_label_quality.py tests/test_generate_pseudo_labels.py tests/test_checkpoint_tool_contracts.py tests/test_confidence_weighted_loss.py -q --no-header --tb=short
```

```text
112 passed, 9 warnings in 36.70s
```

This intermediate run verifies actual CPU generation, manual preservation,
consumer filenames and normalization, scoring boundaries, input validation,
failure cleanup, and checkpoint-tool compatibility. Four subsequent regression
cases also belong to the final standard suite: rollback after a later segment
fails, temporary standalone caching, and two symlinked-source write refusals.
Warnings concern CPU DataLoader pinning. Counts across suites overlap.

### Required smoke test

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
```

```text
--- 8/11 passed, 3 skipped, 0 failed in 22.4s ---
```

Smoke checks pass. Two skips require absent training URI/label fixtures; the
third requires optional `batchgeneratorsv2` transforms. A real local fixture in
the new regressions independently exercises label generation and dataset reads.

### Lint, formatting, and whitespace

```sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/pseudo_label_artifacts.py scripts/generate_pseudo_labels.py scripts/iterative_pseudo_labeling.py scripts/pseudo_label_quality_report.py scripts/labeling/generate_pseudo_labels.py scripts/run_validation_tests.py src/vesuvius_autoresearch/core/patch_catalog.py src/vesuvius_autoresearch/core/vesuvius_loader.py tests/test_pseudo_handoff_contracts.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/pseudo_label_artifacts.py scripts/generate_pseudo_labels.py scripts/iterative_pseudo_labeling.py scripts/pseudo_label_quality_report.py scripts/labeling/generate_pseudo_labels.py scripts/run_validation_tests.py src/vesuvius_autoresearch/core/patch_catalog.py src/vesuvius_autoresearch/core/vesuvius_loader.py tests/test_pseudo_handoff_contracts.py
git diff --check
```

```text
All checks passed!
9 files already formatted
```

All changed Python files pass using existing cached tools. Whitespace checks pass.

### Repository typing

```sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
```

```text
Found 16 errors in 13 files (checked 621 source files)
```

This check remains failing with the same existing diagnostics: missing library
stubs, OpenCV overloads, augmentation slice types, and loader/training tensor-list
annotations. None originate in the new helpers or changed loader import; two
existing diagnostics remain in unmodified sections of the loader file.

### Documentation, claims, filing, and upstream parity guards

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py -q --no-header --tb=short
```

```text
106 passed, 16 skipped in 37.46s
```

These guards pass. Skips require the absent sibling ScrollGT checkout or external
render artifacts. A final focused reference/claim check also passes:

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
```

```text
16 passed in 5.35s
```

## Edge cases considered

Known manual background and ink versus positive/negative/ignore pseudo values;
manual-only and pseudo-only segments; missing/orphan manual masks; RGB, grayscale,
nonfinite, ambiguous, empty, misaligned, and oversized labels; shallow volumes;
incomplete/nonfinite checkpoint weights; malformed/duplicate JSON; duplicate
segment identities; existing/source-aliased output; empty requested region;
declared holdout overlap; no confidence or confidence outside the requested
region; child failure, timeout and interruption; changed inputs; working-directory
independence; actual PNG normalization and residual ignore weight.

## What was not tested

GPU inference, full-size scroll data, actual retraining or repeated learning
rounds, teacher lineage, held-out independence, probability calibration, scientific
quality gains, or competition eligibility. Historical pseudo-label measurements
were not regenerated; corrected undefined metrics and coverage need independent
re-evaluation before interpreting new results. Tiny zero-weight real models establish
mechanical contracts only. CT bytes are not fully hashed, so inputs must remain
stable. Publication assumes serialized writers. Repository typing errors and
previously documented optional/upstream limitations are reported separately.

## Reviewer focus

Check manual-known mask semantics against the consumer filename and normalization
contract; truthful separation of preparation, training, and quality evidence;
all-or-nothing failure cleanup; the pinned sampler import; and explicit limits on
ignore weighting and lineage.
