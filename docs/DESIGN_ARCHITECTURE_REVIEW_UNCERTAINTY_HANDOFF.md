# Proofreader uncertainty handoff: design and architecture review

Reviewed the regional prediction-to-proofreading boundary on main
`b37340e6243b7c51fa4a8d73be2b2aae03b0f283`. All reproductions use temporary
synthetic masks, checkpoints and CT; no study data or measurements were updated.

## Findings and repairs

- **An empty result left an earlier nonempty mask (P2).** A 0.5-probability
  model exported 143 selected pixels, then a confident rerun overwrote the
  prediction but retained those 143 flags because zero masks were skipped.
  Complete runs now publish zero masks too, with an explicit EMPTY status.
- **A failed Zarr write destroyed the prior store (P2).** Opening the target
  with mode `w` replaced its contents before chunks finished. Injecting a write
  failure left the old all-one mask overwritten. The new publisher builds in a
  sibling staging directory and installs only after chunks and attributes have
  been written. Installation errors use the existing directory publisher's
  rollback. Existing root directory permissions survive replacement.
- **Multiple channels were silently discarded (P2).** A C/Z/Y/X input was
  reduced to its first channel regardless of C. Export now accepts H/W, Z/Y/X
  or singleton-channel C/Z/Y/X, and refuses empty/ambiguous shapes and invalid
  binary data. Binary encodings 0/1 and 0/255 normalize to the legacy float32
  0/1 store. Tensors are detached; low-precision entropy endpoints remain finite.
- **The prediction did not identify its proofreading result (P2).** Sidecars
  now report EXPORTED, EMPTY, SKIPPED, INCOMPLETE or UNAVAILABLE, with a path
  only for a current mask. Partial shards are not exported as full uncertainty
  maps. Optional import failures retain a reason; storage errors still fail the
  run without publishing success metadata. Mask attributes record shape/axes,
  encoding/count and supplied source context, including the prediction recipe
  and loaded checkpoint digest.
- **Module launches could import another checkout's core (P2).** Two subprocess
  tests reproduced `python -m` selecting a foreign editable package. Both the
  sampler and regional prediction entry point now prepend their own root/src
  for direct and module launches.

The three initial regressions failed before repair (3 failed in 3.20s). The
additional two launch regressions failed during review (2 failed in 9.06s),
then passed after the source bootstrap correction.

## Architecture and user workflow

`scripts/uncertainty_artifacts.py` owns mask validation, output planning,
attributes and staged publication. The sampler's existing export function is
a thin tensor/NumPy adapter and returns an export record. Existing destinations
require a boolean `overwrite=True`; prediction explicitly refreshes its planned
mask. Destination validation rejects URI-like or empty outputs, source aliases,
symlinks/special files/hard links and unrelated stores. Source paths must be a
sequence rather than an accidentally iterable single string.

The existing production output-tree checker moved to the stdlib-only
`core/prediction_artifacts.py` with compatibility wrappers in
`scripts/production_artifacts.py`. Production messages and entry limits remain
intact; both callers share the same filesystem policy. The established
`staged_directory` publisher is reused rather than adding another rename and
rollback implementation.

The regional path resolves its names, checks the mask budget and validates the
destination before model work, then rechecks before publication. Its inference
probabilities, TTA, blending and scoring formulas are unchanged. The bare Zarr
format, float32 0/1 encoding and `(1, 64, 64)` chunks remain compatible; source
attributes do not make a projected diagnostic a 3D confidence volume. See
[checkpoint analysis](CHECKPOINT_ANALYSIS.md#proofreader-uncertainty-masks) for
status meanings and the Python API.

## Verification and limits

Python 3.10.21 / NumPy 2.2.6 / Torch 2.9.1+cpu / Zarr 2.18.3; Villa pinned at
`ccb431818fa68059138f2c964ae299fc474ff116`. Exact final commands and captured
outputs are in the PR, including the affected curated selection, required
smoke, repository-wide Mypy, scoped Ruff and document/claim guards.

- Affected curated selection: **308 passed in 43.33s**, across 9/197 modules.
- Document/claim guards: **138 passed, 1 skipped in 34.57s**; the live spiral
  corpus is unavailable here.
- Repository-wide Mypy: **943 source files passed**. Ruff lint/format passed all
  seven changed Python files.
- Required smoke: **8/11 passed, 3 skipped, 0 failed in 12.8s**. Local training
  data and an optional transform were unavailable; available model/import and
  augmentation checks passed, including 288/288 checkpoint tensors.

Tests exercise real Zarr stores and a small regional predictor, with synthetic
CT/checkpoints and stub neural networks. They cover failed chunks and install
rollback, prior-store preservation, legacy replacement, modes, invalid masks
and metadata, budgets, source aliases and late swaps, confident reruns, skip/
shard/import statuses, failed-run metadata invalidation and checkout isolation.

No full curated suite, CUDA/RTX 4090 workload, real-scroll proofreading session,
full-region peak-memory/runtime benchmark or new scientific result was produced.
The voxel budget is not an RSS/VRAM limit. Callers must serialize readers/writers:
replacement has a short path gap, is not a power-loss transaction and does not
make all prediction artifacts one transaction. Earlier prediction arrays may be
new if mask publication fails. Skipped/unavailable masks left on disk are
historical; consumers must follow current sidecar status/path. Supplied context
is not independent spatial registration or uncertainty calibration.
