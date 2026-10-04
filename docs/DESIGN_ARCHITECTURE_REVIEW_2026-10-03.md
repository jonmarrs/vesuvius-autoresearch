# Design and architecture review — 2026-10-03

Reviewed baseline `6acd1295`, concentrating on the newly added interpolation
study and the separate CT-volume production prediction path. The earlier
fragment-detector and orchestration fixes remain covered by standard validation.
The branch was subsequently rebased onto `0b1a78f8`; standard validation, smoke
checks, documentation guards, and mypy were rerun against that revision.

## Findings and repairs

| Priority | Verified problem | Repair |
|---|---|---|
| P1 | Production prediction crashed while constructing the model because its CLI lacked fallback attributes. It then expected `model` instead of the training checkpoint's `model_state_dict`, treated loader tensors as NumPy arrays, and lacked voxel metadata arguments. | Reuse the shared model factory and normalized loader with checkpoint-derived patch size, depth, features, and ridge channels. Load weights strictly, accept the legacy weight key, and use one batching path for full and final partial batches. |
| P1 | Hann weights were zero at the outer boundary, so border predictions became black. Invalid or undersized regions could produce negative tile coordinates or gaps. | Use positive Hann weights, include terminal tile positions, validate stride/region/batch settings, and reject reads beyond the volume. |
| P1 | Exported OME-Zarr translations used x/y/z voxel indices where the metadata declared z/y/x micrometers. The root also lacked the required Zarr group marker. | Reverse and scale the origin, preserve source provenance and effective voxel size, and create an actual Zarr group. Metadata keeps the original x/y/z voxel indices for callers. |
| P1 | Smoke comparisons used truncating `zip`, accepting incomplete or misnamed slice sets and emitting reports for incomparable crops. | Share a reader that requires all five named slices and validates image dimensions, types, and crop bounds before output. Compare matching slices strictly. Full-render layers are cropped individually before retention to reduce memory use. |
| P1 | Window analysis ignored the saved `WINDOWS` list, accepted fewer than eight windows, and trusted metrics without checking the crop area. | Recompute the registered coverage choice, compare it with the recorded manifest, require the complete selection, and validate summary/strip counts, finite scores, and gap counts. Invalid inputs do not replace an existing report. |
| P2 | Zero linear foreground counts became `None` and crashed median/min/formatting operations. | Preserve undefined relative deltas as JSON null, count them, and mark the all-window foreground prediction indeterminate. Positive-baseline calculations retain their original definitions. |
| P1 | Bash process substitution discarded selector failures; the surface hash was checked only once despite the registered per-window requirement. | Capture selection status before accepting output and check the surface before every arm, including the paired mode. Claim output directories atomically and propagate preparation/disk-check failures. |
| P2 | Direct launcher execution used mutable scoring helpers, and frozen drivers could lose the original repository path. The smoke launcher recorded image SHA output without requiring a successful read or matching revision. | Freeze all driver-side helpers, preserve the source repository in snapshots, honor relocatable data paths, verify sampler revisions, and require the expected output slices. Optional resource timing no longer prevents rendering on hosts without `/usr/bin/time`. |

## Architecture and operator experience

There are two supported local prediction contracts: converted fragments with
Lightning detector checkpoints, and CT volumes with research-loop checkpoints.
The README now identifies which command consumes each. The repaired production
command uses the existing factory and loader instead of assuming a separate
checkpoint format or input normalization. CLI geometry errors occur before any
prediction artifact is written. Output coordinates and units are explicit.

For the interpolation study, `scripts/interpolation_inputs.py` provides a common
TIFF contract to smoke comparison and strip construction. It sits beside the
analysis scripts so the launcher's frozen copy can import it independently of
the live repository. The chain now follows this evidence flow:

```mermaid
flowchart LR
    Selection[Coverage selection succeeds] --> Manifest[Eight recorded windows]
    Manifest --> Surface[Surface hash verified per arm]
    Surface --> Render[Render succeeds]
    Render --> Slices[Five valid named slices]
    Slices --> Score[Existing pinned scoring recipe]
    Score --> Analysis[Manifest and metrics validated]
    Analysis --> Report[Defined and undefined changes reported]
```

The registered selection algorithm, predictions, sampler revisions, crop
dimensions, max-composite/p95/JPEG recipe, and scorer remain unchanged for valid
inputs. A byte-for-byte JPEG regression verifies the strip recipe. No published
report, checkpoint, or villa submodule was modified. The existing preregistration
is retained as the original research record.

## Verification

The initial regression run produced **13 failures and 4 passes** before fixes.
It reproduced missing-slice truncation, wrong slice identity/type, invalid crop
bounds, unchecked window manifests, incomplete selections, zero denominators,
prediction startup failures, and incorrect OME translations. A later regression
also demonstrated that the output could not be opened as a Zarr group.

- Standard validation: **108 passed, 1 skipped**, using
  `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py`.
  The suite now includes interpolation input/launcher and production prediction
  regressions. The skipped test is the opt-in live S3 check.
- Production tests use a real local Zarr volume and saved weights. A constant
  model checks normalized input, partial batches, every boundary pixel, geometry,
  and metadata. A real small ResEnc checkpoint reload matches direct model output
  to uint8 quantization tolerance.
- `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py`:
  **8 passed, 3 skipped, 0 failed**; all 288 compatible production checkpoint
  tensors loaded. Skips require two missing training-data fixtures and the
  unavailable upstream augmentation pipeline.
- Ruff 0.9.10 lint and formatting checks cover every changed Python file. Shell
  syntax checks, Python compilation, CLI help, and `git diff --check` pass.
- The nine-file documentation guard suite configured in `.pre-commit-config.yaml`
  passed **92 tests, with 1 skipped** for an unavailable external render artifact.
  After rebasing, the same suite plus `tests/test_filing_2026_10_numbers.py`
  passed **102 tests, with 1 skipped**.
- Repository-wide mypy 1.19.1, using the project interpreter, reports the same
  **17 pre-existing errors in 14 files** before and after the fixes: missing
  requests/YAML stubs and existing OpenCV, NumPy, optional-tensor, and teacher-logit
  annotations. There are no new diagnostics. This full type-check gate is not
  reported as passing.
  Command: `UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python`.

## Validation limits

Launcher tests use local executable stand-ins. Actual sampler containers, live
S3, GPU inference, long-running renders, and full research volumes were not run.
No new accuracy, interpolation-effect, or throughput claim follows from these
checks. Rerunning the unchanged preregistered study requires its actual data and
pinned scoring environment.

The production predictor retains dense output accumulation and therefore uses
memory proportional to the requested output region. This repair does not add
distributed inference, out-of-core blending, or TTA. The separate upstream
production wrapper is outside this change.
