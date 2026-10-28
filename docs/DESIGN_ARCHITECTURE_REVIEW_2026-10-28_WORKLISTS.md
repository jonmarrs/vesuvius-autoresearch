# Candidate worklist design and architecture review — 2026-10-28

Reviewed geometry planning, ranked-table loading, generated evidence commands,
pipeline report paths and shared publication against main
`076fe2700f5b09a402fc2b9b8e5be694db4ccd6a` (PR #276). Work used an isolated
checkout and synthetic inputs with CUDA hidden. No live study data, journals,
research-host files, processing jobs or prize submissions were used.

## Findings and resulting behavior

- **Destructive worklist outputs.** The CLI wrote JSON and TSV directly and
  independently. Four reproductions accepted the ranked input, checkpoint,
  shared JSON/TSV destination and a path inside the source volume as outputs.
  Output planning now checks aliases, ancestors, symlinks and existing inode
  identities together with named inputs and planned artifact directories.
- **Partial legacy publication.** Both files are now staged and verified before
  replacement. A caught publication error attempts to restore both prior files.
  Existing file modes are retained. If restoration fails, backups remain in
  named recovery directories rather than being deleted during cleanup.
- **Mutable candidate identity.** Generated evidence commands formerly selected
  a numeric row from a mutable ranked file and used execution-time relative
  paths. New commands pin SHA-256 and the planning directory. Evidence selection
  checks the digest and parses the same captured bytes before touching output.
  Checkpoint/crop paths are absolute; row-relative inputs use the recorded base.
- **Ambiguous TSV parsing.** Duplicate headers and inconsistent row widths were
  accepted by DictReader. The shared reader now rejects these and malformed
  quoting/UTF-8, and bounds the complete source to 16 MiB/100,000 records before
  filtering or limiting. Blank lines and quoted multiline cells retain their
  existing parsed-candidate indexing semantics.
- **Captured inputs omitted from report protection.** Pipeline path validation
  reloaded the current table but protected only captured work-item output paths.
  It now protects captured source and mask paths too, even if the table differs.

## Review-bundle feature

`--bundle-dir` publishes a new directory with JSON, TSV, README and the exact
ranked-source capture. Its evidence commands reference that captured source.
Selection counts include unknown occupancy; JSON exposes each priority component
using the unchanged heuristic. Priority and the legacy submittable flag do not
establish model quality or prize eligibility. Explicit `--checkpoint` supports
planning against the intended model path without loading weights.

Existing default JSON/TSV paths and Python `build_worklist` callers remain
supported. Legacy commands refuse a rewritten source rather than silently
retargeting a row. Bundles retain their source independently. Arrays, masks,
checkpoint contents and scripts are not frozen by a bundle.

The generic bounded UTF-8 `Snapshot` moved to `scripts/text_snapshot.py`, shared
by candidate planners and experiment reports. The reports re-export the same
class name and retain their existing contract. File-pair publication has a small
separate helper; immutable bundles reuse the existing directory publisher.

## Verification and review corrections

The four output-alias regressions failed on the baseline. Tests cover source
drift, restored pairs, deliberately failed rollback retaining backups, file
modes, malformed/BOM/multiline TSV, full-source budgets, selection/priority
explanation, captured pipeline inputs and digest failure before evidence output.
The new test module is registered in the standard validation list.

An actual generated command runs prerequisite-only evidence preflight from a
different directory after the original TSV has changed. This caught an initial
implementation error: resolving the interpreter symlink bypassed its virtualenv.
Paths now become absolute without dereferencing that symlink. The test does not
load checkpoint weights or run inference, and its prerequisite PASS has that
limited scope.

Commands from `/workspace/vesuvius-geometry-review`:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' MPLCONFIGDIR=/tmp/vesuvius-worklist-mpl /tmp/vesuvius-review-env/bin/python -m pytest -q -rs tests/test_worklist_planning_contracts.py tests/test_lasagna_fiber_worklist.py tests/test_candidate_preprocessing_contracts.py tests/test_ranked_inference_planning.py tests/test_candidate_content_provenance.py tests/test_prize_readiness.py tests/test_summarize_villa_evidence_preflight.py tests/test_post_sprint_villa_handoff.py tests/test_validation_suite_covers_the_loop.py tests/test_experiment_report_contracts.py tests/test_report_time_and_selection.py tests/test_daily_report.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
/tmp/vesuvius-pr256-lint/bin/ruff check scripts/worklist_publication.py scripts/text_snapshot.py scripts/experiment_report_data.py scripts/inference/run_ranked_inference.py scripts/build_lasagna_fiber_worklist.py scripts/run_villa_prize_evidence_chain.py scripts/execute_lasagna_pipeline.py scripts/run_validation_tests.py tests/test_worklist_planning_contracts.py
/tmp/vesuvius-pr256-lint/bin/ruff format --check scripts/worklist_publication.py scripts/text_snapshot.py scripts/experiment_report_data.py scripts/inference/run_ranked_inference.py scripts/build_lasagna_fiber_worklist.py scripts/run_villa_prize_evidence_chain.py scripts/execute_lasagna_pipeline.py scripts/run_validation_tests.py tests/test_worklist_planning_contracts.py
PYTHONPATH=/tmp/vesuvius-pr256-types python3 -m mypy --follow-imports=skip --explicit-package-bases --namespace-packages --cache-dir /tmp/vesuvius-worklist-mypy scripts/worklist_publication.py scripts/text_snapshot.py scripts/experiment_report_data.py scripts/inference/run_ranked_inference.py scripts/build_lasagna_fiber_worklist.py scripts/run_villa_prize_evidence_chain.py scripts/execute_lasagna_pipeline.py scripts/run_validation_tests.py tests/test_worklist_planning_contracts.py
git diff --check
```

Final results: **320 passed in 111.41 seconds**, including 24 new cases. Smoke:
**8 passed, 3 skipped, 0 failed in 14.5 seconds**. The two data-loader smoke
checks lack local training inputs, and the optional bg2 augmentation entry point
is unavailable. A Fontconfig cache warning did not fail the smoke test. Ruff
and formatting passed for nine files; targeted mypy reported no issues in nine
files with imported implementations skipped. Diff whitespace checks passed.

The initial broader preprocessing run hit eight missing-runner failures in the
uninitialized review submodule. The existing cached pinned runner was copied
into this checkout and verified against Git blob
`531948c2a6a88596718bde8beb0325554ec41b3b` from pinned Villa commit
`ccb431818fa68059138f2c964ae299fc474ff116`. Tests use a controlled upstream
subprocess fixture; no native tensor/GPU runner was executed or dependencies
installed. This file is test input only and is not a submodule update.

## Limits

Legacy two-file publication requires serialized readers/writers and is not
atomic across paths or crash-transactional. A killed process can leave staging
and backup directories. The new bundle provides one immutable directory instead.
Keep source paths stable during planning and input contents stable during jobs.
Native GPU performance, full-scroll processing, scientific gains, complete source
provenance and prize eligibility remain untested. This review covers the changed
planning boundaries, not every component of the research system.
