# Ranked inference and artifact review

Reviewed October 28, 2026 against public main
`aa694ad33a6b935e9bf34d9b8fbeca8b32264b6a` in a separate checkout. The review
covers the queue, ranked command planner, regional predictors, artifact
consumer and smoke check. No live research measurements or GPU jobs were used.

## Findings

1. **Different scrolls could overwrite the same prediction family.** The
   coordinate-based default name contains no source identity. An isolated
   baseline reproduction selected two scrolls at identical coordinates: the
   old runner accepted both commands with one shared image/metadata destination.
   The full batch now checks planned artifact families before writing or
   executing. A new optional queue flag, `--namespaced-artifacts`, produces
   scroll/division-specific stems for new tables. Legacy tables retain their
   names and receive a useful collision error when unsafe together.
2. **Custom stems did not select the saved arrays.** The command builder used
   a row's custom stem for its image and sidecar while the predictor still wrote
   coordinate-named arrays and exports. The ranker also ignored the custom
   field. A shared stdlib naming helper now validates stems; both predictors
   accept `--artifact_stem`, and the ranker honors it. CPU tests run both
   prediction paths on two synthetic scrolls with identical coordinates, check
   the first output's bytes and mtimes survive the second run, and rank both.
3. **Manifest publication could destroy an input or a prior plan.** A manifest
   path aliasing the checkpoint or ranked table was opened with truncation.
   Planned outputs and the manifest now share one path check covering inputs,
   existing inode aliases, symlink targets and directory containment. Complete
   command serialization precedes writing, and publication uses a temporary
   file and atomic replacement with the established file-mode helper.
4. **Invalid selection looked successful.** A nonpositive limit used Python
   slicing, and no eligible rows published an empty script with success. Both
   now fail with an actionable CLI error before manifest publication.
5. **Smoke could exercise another checkout.** It inserted the repository root
   but omitted its `src/`, letting a shared editable environment provide older
   package code. The new artifact helper exposed this as an import failure.
   Smoke now prioritizes its own root and source package, and enforces its
   documented CPU visibility even when CUDA was enabled in the environment.
   A subprocess regression simulates a foreign editable package and an enabled
   GPU without importing Torch.

## Architecture and scope

`core/prediction_artifacts.py` holds stdlib naming and path validation. Geometry
and source binding remain the existing predictors' and ranker's responsibilities.
The planner reserves each job's whole artifact family, including optional
fiber/shard exports. Path comparison uses resolved paths, inode identities and
a component-sorted ancestor walk, so unrelated names cannot hide a nested
collision. Read/read overlap is allowed; writes must be separate.

This is a batch planning contract. It does not reserve the GPU or coordinate
arbitrary external writers. Existing single-candidate outputs can be replaced
on an intentional rerun. The guarded handoff remains the execution entry point;
there is no new background scheduler or training change. Queue namespacing is
opt-in to retain access to existing coordinate-named artifacts. No historical
outputs, benchmark values, filing claims or registrations were rewritten.

## Verification

The tests exercise CLI refusal before job launch, full-family collisions,
checkpoint/table aliases through direct paths, symlinks and hard links, nested
Zarr outputs, atomic publication failure and permissions. A `python -S`
subprocess proves planning works without site packages from another directory.
Another test covers namespaced queue generation through ranking and planning.

The cached Python 3.10 environment is `/tmp/vesuvius-review-env`; commands use
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CUDA_VISIBLE_DEVICES=''`:

```sh
/tmp/vesuvius-review-env/bin/python -m pytest -q -rs \
  tests/test_ranked_inference_planning.py tests/test_candidate_ranking_contracts.py \
  tests/test_prize_readiness.py tests/test_submission_contracts.py \
  tests/test_lasagna_fiber_worklist.py tests/test_smoke_checkout.py \
  tests/test_validation_suite_covers_the_loop.py tests/test_volume_inference_contracts.py

CUDA_VISIBLE_DEVICES=0 /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
# 8 passed, 3 skipped, 0 failed in 15.2 seconds
```

The final integration run passed **308 checks with 17 skips in 57.31 seconds**.
The skips are coherence cases requiring the unavailable Villa `nrrd` dependency.
An earlier integration run passed 189 checks; a focused planning/smoke guard
run passed 38. The first smoke run exposed the foreign-checkout import problem;
the final smoke run passes with its three data/augmentation skips disclosed.
The full repository suite, GPU inference and real-scroll inference were not
run. Synthetic model and CT fixtures establish behavior, not model quality.

Ruff passes on all 11 changed Python files; targeted mypy passes on six
stdlib planning, queue, smoke and test modules. Diff and documentation link
checks pass. A real queue CLI invocation with the namespace flag produced two
distinct names for Scroll 2 and Scroll 3 at equal coordinates.
