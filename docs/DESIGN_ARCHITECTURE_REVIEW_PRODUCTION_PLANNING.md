# Production inference: design and architecture review

Reviewed the production CLI's input, planning, execution and output boundary at
base `34e18c01746f54f2273efc22c61c337421d5bdfc`. This is a scoped review,
not certification of the repository or a new research result. All collision
reproductions used temporary synthetic inputs; no study data was modified.

## Findings and repairs

1. **Production could overwrite its own inputs (P1).** A CT OME-Zarr group at
   the planned output name passed inference and was replaced with the output
   array. A checkpoint at the planned metadata name was loaded, deleted during
   sidecar invalidation, then replaced by JSON. Both fixtures expected refusal
   and failed on the original implementation. The new `ProductionArtifactPlan`
   rejects output/input overlaps, aliases and unsafe existing output entries
   before checkpoint/model work, and checks them again before publication.
2. **An external OME level could hide a collision (P1).** During review of the
   initial fix, a group whose `0` symlink pointed inside the planned output
   still reproduced input replacement. Planning now protects both the source
   root and its selected, resolved array. Inference reads that selected path.
3. **Production metadata did not identify loaded checkpoint bytes (P2).**
   `checkpoint_sha256` was null. Capturing a bounded regular file once allows
   both hashing and deserialization to consume the same bytes. Metadata also
   records their byte count. A test replacing the checkpoint path during load
   verifies that the record still describes the captured model, not later bytes.
4. **Planning required starting inference, and comparisons reused names.**
   `--dry-run` emits a JSON plan with geometry, calibration, configuration,
   recipe, tile count, paths and captured-checkpoint identity. `--artifact-stem`
   lets users retain separate runs of a region. Default names remain compatible.
   A direct script invocation also resolves imports from its own checkout.

The initial three regression cases failed with two `DID NOT RAISE` collisions
and a null digest mismatch. The additional external-level regression failed
with `DID NOT RAISE` before the selected-array repair.

## Architectural decisions

The artifact plan owns naming and filesystem inspection, without creating
directories or loading models. The CLI owns checkpoint/configuration validation,
metadata-only source opening, geometry checks, execution and metadata-last
publication. It returns before model construction and voxel reads for a dry run;
tile counts are computed arithmetically without allocating a grid.

The volume wrapper exposes its existing local path/file-URI normalization and
array selection so the planner and reader agree. Output inspection refuses
symlinks, hard-linked files and special entries throughout an existing output
group. It is bounded at 100,000 entries, rather than scanning the CT dataset.

The existing UTF-8 snapshot helper delegates descriptor-safe byte capture to
`capture_bytes`; text decoding and snapshot verification retain their contract.
Capture checks the actual regular-file descriptor and a positive byte limit,
reads only the observed size plus one byte, then checks size and observed
timestamps. This avoids reserving the entire 4 GiB default budget for a small
checkpoint and detects observed concurrent growth, truncation or replacement
of the open file's contents. Nonblocking descriptor opening retains the existing
POSIX FIFO-replacement protection. Configuration must be serializable as finite
JSON before model work, avoiding a late metadata error for invalid settings.

## Verification

Used Python 3.10.21, Torch 2.9.1+cpu and the pinned Villa submodule
`ccb431818fa68059138f2c964ae299fc474ff116`. CPU review environment only;
dependency synchronization that would install CUDA was not run.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib \
XDG_CACHE_HOME=/workspace/.vesuvius-review-cache \
/workspace/.vesuvius-review-env/bin/python scripts/run_validation_tests.py \
  --match '*production*' --match '*text_snapshot*' \
  --match '*volume_inference_contracts*' --match '*volume_read_contracts*' \
  --match '*volume_cartographer*' --match '*validation_runner*' \
  --match '*validation_suite_covers_the_loop*' --match '*workspace_status*' \
  -- --tb=short
```

Result: `Validation scope: 10/183 curated modules`; `316 passed in 34.69s`.
The selected scope covers production, shared source snapshots, local volume
contracts, workspace-status snapshot consumers and validation-runner registration.
A final focused follow-up after adding calibration/configuration to the plan
passed all 56 cases in production planning, production inference and byte/text
capture. Exact commands and outputs are recorded in the PR.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
MPLCONFIGDIR=/workspace/.vesuvius-review-cache/matplotlib \
XDG_CACHE_HOME=/workspace/.vesuvius-review-cache WANDB_MODE=disabled \
/workspace/.vesuvius-review-env/bin/python scripts/smoke_test.py
```

The smoke check passed 8/11, with 3 skips and 0 failures. Training-data loader
checks lacked their local URI/labels; the optional batchgenerators transform
was unavailable. Ruff lint/format and scoped Mypy checks cover all seven
changed Python files; exact commands and outputs are in the PR.

## Limits and remaining work

- A dry run deserializes trusted checkpoint tensors on CPU. It does not verify
  weight/model compatibility, voxels, ridge computation, GPU availability or
  capacity. Its verification flags say so. The capture limit is not an RSS cap.
- Checks are filesystem observations, not locks or an atomic dataset snapshot.
  Keep paths stable and serialize writers. Source chunks are not recursively
  scanned or hashed; arbitrary aliases inside the source are not audited.
- Publication keeps the existing metadata-last contract. After invalidation,
  a write failure can leave an incomplete Zarr without metadata. There is no
  multi-artifact transaction, rollback or automatic repair of older outputs.
- The full curated suite, GPU inference, remote volumes, native VC3D and
  full-scroll production workloads were not exercised. No training, benchmark
  or prize-evidence claims were added.

Usage and rerun behavior are documented in
[CT-volume inference](VOLUME_INFERENCE.md#production-planning).
