# Design and architecture review — the owner's #273–#277, #279 and #280 (inference, candidates, reports, evidence)

Date: 2026-10-28. Baseline: `289f9ffb` (main after the owner's #280).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 15:19–23:12 UTC firings. Three read-only reviews ran beside mine: inference and candidates
(#273, #274, #277), reports and review queues (#275, #276), and evidence and the validation runner (#279, #280). I
checked each of their findings before acting on it. #278 and #281–#284 merged while this was under way; this branch
merges them so that it merges cleanly, and the next round reviews them.
- **#273** plans ranked inference artifacts so that two candidates cannot write the same files.
- **#274** records each candidate crop's and structure tensor's content and checks it before reuse.
- **#275** makes the experiment reports independent of the runner's timezone and selects rows by append order.
- **#276** makes the active-learning review queue deterministic and refuses unsafe outputs.
- **#277** captures geometry worklists with their sources and publishes them as pairs.
- **#279** preflights the prize evidence chain and its validator.
- **#280** makes the standard suite checkout-aware and adds explicit test selection.

## What changed

- **A failed pipeline run no longer leaves an old PASS report** (`scripts/execute_lasagna_pipeline.py`).
  - The report-path check reads the ranked table to learn which candidate files the report must not replace. A
    table that cannot be read gave no candidates, and the run went on to write a FAIL report.
  - #277 moved the table reader onto `Snapshot`, which raises `ValueError`, not `FileNotFoundError`, for a missing
    or malformed table. The run then exited as an "unsafe pipeline report path" and left the previous report, PASS
    or not, in place. `docs/CANDIDATE_PREPROCESSING.md` says a new attempt invalidates the old report.
  - An unreadable table now falls through as before. A test in `tests/test_worklist_planning_contracts.py` runs
    `main()` on a missing and a malformed table; both cases fail on the old script.
- **The validator's `--out` writes the FAIL for a remote `file:` reference** (`scripts/validate_prize_artifact.py`).
  - Before #279, metadata naming `file://nas/...` was reported as FAIL with or without `--out`. #279 resolves every
    referenced path to plan the report's write. The remote URI raised there, so with `--out` the CLI exited 1
    before writing, and an earlier PASS report stayed on disk.
  - A reference that names no local file cannot be the report, so planning now skips it. The validation fails on
    it as before, and the FAIL replaces the earlier report. A test in `tests/test_evidence_workflow_contracts.py`
    fails on the old validator.
  - The owner's deliberate abort, which keeps the previous report when the metadata changes mid-validation, is
    unchanged.
- **`predict.py` and `ensemble_predict.py` import this checkout's package** (`scripts/inference/`).
  - The ranked planner launches `predict.py` by path. Both scripts put only the checkout's root on `sys.path`, so
    `vesuvius_autoresearch`, including #273's `prediction_artifacts`, came from the shared `.venv`'s editable
    install. `pyproject.toml` notes that install may point at another checkout.
  - They now add `src` as #273's planner and `smoke_test.py` do. The test in
    `tests/test_ranked_inference_planning.py` puts a foreign package first on the path and fails on the old scripts.
- **The review queue refuses a repeated catalog coordinate** (`scripts/active_learning_sampler.py`). With the
  default spacing of 0, a repeated patch was scored, ranked and counted twice. The test in
  `tests/test_active_learning_queue_contracts.py` fails on the old sampler.
- **Two files pass the pre-commit `ruff-format` hook again:**
  - `scripts/inference/predict.py`, unformatted since #274;
  - `tests/test_volume_inference_contracts.py`, unformatted since #273.

  `ruff format` changes no syntax tree.
- **The standard suite was red on main.** #279 moved `_load_json` onto `Snapshot`. A missing metadata file then
  raised `ValueError`, where `test_volumetric_label_contracts.py` (in `VALIDATION_TESTS`) expected
  `FileNotFoundError`. This branch updated the test; the owner's #278 made the same change, and the merge keeps it.

## Verified, no change needed

- **#273–#277** (the inference and candidates review, and the reports and review-queue review).
  - Hashes are taken over the bytes used:
    - `predict.py` hashes the checkpoint bytes it loads;
    - the crop hashes its source region before and after the copy and publishes from staging;
    - tensors re-check their source crop.
  - The atomic writers publish from a temporary file in the same directory and keep file modes. Their rollback
    keeps backups when it cannot restore.
  - Refusals come before any write: the ranked planner exits 2, the worklist 1 (or 2 for its flag conflict).
  - Default artifact names are unchanged without `--artifact_stem`.
  - #275 is the same on every runner: the manifest and chart are identical under UTC, Europe/London and
    America/Los_Angeles. `--last-rows` takes the last rows in file order, which is right across the fall-back hour.
  - #276's subsample is deterministic and ties keep catalog order. Its entropy is finite in fp16 and bf16. Its output
    is checked before the model loads, and a re-run cannot replace a reviewer's queue.
  - Each PR's new tests fail on its parent.
- **#279 and #280** (the evidence and runner review).
  - Preflight writes nothing. Path planning, the FAIL marker and the removal of old evidence come in that order.
  - Apart from `file:` URIs and a byte-order mark, the validator's verdicts did not loosen:
    - the existing callers' 91 calls agree before and after;
    - of 1,127 variations of a valid record, the only FAIL-to-PASS changes are those two.
  - `--match` with no matching module exits 2 before pytest starts. A selection that runs no test passes pytest's
    exit 5 through.
- **The checks pass** (mine).
  - Ruff 0.9.10 `check` and `format` are clean on the twelve changed Python files.
  - Mypy, with the pre-commit hook's flags, is clean over the whole repository (826 files at `289f9ffb`).

## Observations for the owner (not changed)

- **CT evidence can outlive the source voxels it was made from** (#274, `scripts/execute_lasagna_pipeline.py`).
  - Evidence is reused when this run reused the crop. If the source changed, an earlier run without
    `--with-evidence` rebuilt the crop, and this run reuses both.
  - The inference review reproduced this with the real crop and tensor code.
  - The evidence chain records no hash of the region it read. Recording the crop's `content_sha256` in the evidence
    and comparing it would close this, and would also stop evidence re-running after an identical rebuild.
- **The review queue scores each patch at a depth that depends on its catalog index** (#276).
  - `VesuviusLabeledDataset` draws the depth window with `RandomState(idx)`. The evaluation budget, the subsample
    and the sort change each patch's index, and so its slices and score.
  - Entries record only y/x. This predates #276, which kept the subsample and added the budget flag.
  - Fixing it means choosing which depth the queue scores.
- **A sparse zarr volume with no fill value cannot be cropped.** Missing chunks read back as uninitialised memory,
  so the crop's two source hashes differ and it always refuses. Before #274 it copied the garbage. Worth checking
  the scroll volumes' `.zarray` fill values.
- **The evidence chain** (#279, mostly older):
  - A failed unpinned run checks only the row's paths before clearing old evidence, not masks named in the old
    metadata. A mask named like a managed evidence file could be removed.
  - Planned writes are not checked for links. A symlink or hard link at `predict_command.sh` or a prediction file
    writes through to its target.
  - Preflight raises instead of reporting FAIL on a remote `file:` mask in existing metadata.
- **#280:** a `--match` subset or a pytest filter exits 0 like a full run, and the banner counts modules, not tests.
- **Reports** (#275): the PDF's "Recent" table orders by timestamp label, which puts 01:20 PDT after 01:05 PST across
  the fall-back. The root is `train.py`'s naive `time.strftime` stamps. The SVG's date is the runner's local time
  (older).
- **The sampler by path:** `python scripts/active_learning_sampler.py` now fails to import `scripts`. The documented
  form is `-m`, and nothing in the repository runs it by path.
- **Doc audit:** 531948c2… is a Villa blob, cited by #274's and #277's review documents.

## Verification

- **The changed tests**, with every test of the touched scripts, gave 844 passed, before the validator fix. The one
  failure was the stale test above. The validator's test file then gives 48 passed.
- **The standard suite** (`scripts/run_validation_tests.py`) on the branch gives 43 failures and 2 modules that
  cannot be collected.
  - The same 43 fail on main. They need `s3fs`, `numba`, `jsonschema` or Villa files absent here.
  - The 2 modules need `tensorstore` and `s3fs`.
- **The guard set** with the seven PRs' tests gives 1313 passed and 15 skipped. The one failure is the standing
  `test_live_documents_stay_clean`, with the same 20 paths as before.
