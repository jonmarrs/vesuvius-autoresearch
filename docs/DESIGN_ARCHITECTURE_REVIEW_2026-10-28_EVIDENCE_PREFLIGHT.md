# Evidence workflow design and architecture review — 2026-10-28

Reviewed direct evidence preparation, prerequisite checks, artifact validation,
report publication and their operator documentation against main
`8de858b06a88bfb1c38412109adcb106a32efe20` (PR #277). Execution used synthetic
fixtures in an isolated checkout with CUDA hidden. No live study results,
journals, research-host deployment, prize filing or GPU jobs were used.

## Findings and fixes

- **Preflight disagreed with execution.** It accepted negative/nonfinite or
  malformed coordinates, fractional patch sizes, undersized/empty regions and
  unsafe artifact names that the prediction command refused. It also accepted a
  directory as a checkpoint. Preflight now uses the prediction command builder
  and checks readable, nonempty regular checkpoint files. It does not load or
  validate weights.
- **Outputs could replace inputs.** Evidence preparation could delete a ranked
  TSV supplied at its managed manifest path. Validator `--out` could overwrite
  metadata, masks or the discovery image it inspected. Shared path planning now
  protects named inputs and managed outputs, including ancestor and inode aliases,
  before mutations. A prerequisite report cannot replace final readiness or
  prediction artifacts.
- **Preflight mask arguments were ignored.** The CLI now forwards supplied mask
  paths, checks readability and marks missing unspecified masks `NOT_CHECKED`.
  Fresh inference does not count masks from metadata it will replace; existing
  artifact checks still use that metadata's declared masks.
  File presence does not establish mask content, alignment or overlap.
- **Direct JSON writes could leave partial files.** Evidence records and reports
  now use the shared staged JSON writer. A new attempt publishes its FAIL marker
  before removing stale derived metadata. Failure to publish that marker retains
  the previous coherent package and starts no processing.
- **Metadata interpretation could move with a symlink.** Validation now captures
  bounded metadata once, uses its canonical directory for relative artifacts,
  records its SHA-256/size and checks for changes before returning/publishing.
  A symlink retarget cannot rebase the captured record's relative paths.
- **Malformed inputs could escape the failure-report contract.** JSON rejects
  duplicate fields, nonstandard nonfinite constants and excessive nesting, with
  a 2 MiB limit per JSON source. Numeric overflow produces a failure report.
  Images/masks must be regular files so named pipes are rejected before opening.

The twelve original regression cases all failed on the baseline. They cover the
geometry/checkpoint mismatch and destructive input/output aliases. Additional
cases cover reserved report destinations, mask forwarding, failure-marker
publication, symlink/hardlink aliases, metadata drift/rebasing, serializer errors,
ambiguous/deep JSON and large numeric values.

## Design and architecture decisions

Preflight retains the existing `status`, `failures` and `warnings`, with named
`checks` and `next_actions`. Each check says `PASS`, `FAIL` or `NOT_CHECKED`.
The report identifies prerequisite scope and leaves prize eligibility unassessed.
Checkpoint compatibility, volume contents/bounds and artifact validation remain
explicitly uninspected. The retained window threshold is labeled a local
artifact contract rather than current official guidance.

`scripts/evidence_paths.py` owns the read/write plan and reuses the existing
path-family and alias checks. Fresh inference may replace its own predictions;
existing-artifact mode preserves those inputs. Supplied masks stay protected in
both modes. The validator captures/parses metadata once for path planning and
validation, rather than hashing one version while inspecting another. Common
metadata decoding and artifact-reference collection are reused by the chain.

Publication is deliberately incremental: the FAIL marker precedes processing,
and the final readiness report describes completed local artifact validation.
Individual JSON replacement is staged; the whole directory is not a single
transaction. A rejected unsafe destination or pinned-table mismatch starts no
attempt and preserves prior evidence. Stable inputs and serialized writers are
still required. The chain retains its previous stale-evidence and refreshed-image
checks after an attempt begins.

## Verification

Commands ran from `/workspace/vesuvius-evidence-review` using cached dependencies:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python -m pytest -q -rs tests/test_evidence_workflow_contracts.py tests/test_submission_contracts.py tests/test_prize_readiness.py tests/test_worklist_planning_contracts.py tests/test_summarize_villa_evidence_preflight.py tests/test_post_sprint_villa_handoff.py tests/test_validation_suite_covers_the_loop.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
/tmp/vesuvius-pr256-lint/bin/ruff check scripts/evidence_paths.py scripts/validate_prize_artifact.py scripts/run_villa_prize_evidence_chain.py scripts/run_validation_tests.py tests/test_evidence_workflow_contracts.py
/tmp/vesuvius-pr256-lint/bin/ruff format --check scripts/evidence_paths.py scripts/validate_prize_artifact.py scripts/run_villa_prize_evidence_chain.py scripts/run_validation_tests.py tests/test_evidence_workflow_contracts.py
PYTHONPATH=/tmp/vesuvius-pr256-types python3 -m mypy --follow-imports=skip --explicit-package-bases --namespace-packages --cache-dir /tmp/vesuvius-evidence-mypy scripts/evidence_paths.py scripts/validate_prize_artifact.py scripts/run_villa_prize_evidence_chain.py scripts/run_validation_tests.py tests/test_evidence_workflow_contracts.py
git diff --check
```

Results: **222 passed in 42.28s** across the seven regression modules. Smoke:
**8/11 passed, 3 skipped, 0 failed in 18.3s**; two dataloader checks lacked local
training inputs and the optional bg2 augmentation implementation was unavailable.
Ruff check/format passed for all five changed Python files, scoped mypy reported
no issues in those five files, and the whitespace check passed. These checks
support the local workflow contracts; they do not establish scientific accuracy.

The new module is registered in the lightweight validation runner. Existing
submission tests exercise preservation of original prediction metadata, missing
evidence, failed execution, stale-success invalidation and fresh-output checks.
Worklist tests run an actual generated prerequisite-only CLI command from another
directory. Preflight uses a synthetic nonempty checkpoint file to verify that
only readability is checked; its PASS does not claim checkpoint compatibility.

## Limits

Native GPU inference, full-scroll processing, scientific accuracy, complete
training history and prize eligibility were not tested. Preflight reads file
metadata and bounded JSON, without loading weights or CT/mask arrays. Full
artifact validation still loads masks into memory and does not fingerprint every
referenced artifact or scan Zarr payloads. Path checks are snapshots, and input
contents must remain stable. This review covers the changed evidence boundaries,
not every component of the research system.
