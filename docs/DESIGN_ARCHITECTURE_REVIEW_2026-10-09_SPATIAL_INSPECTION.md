# Design and architecture review: spatial partition and inspection

Reviewed baseline `54e5916c`, following the merged pseudo-label handoff review.
This pass covers spatial mask splitting and the training/validation scan,
ink-density, and sample-visualization tools against the actual dataset contract.

## Findings and repairs

| Priority | Verified problem | Repair |
|---|---|---|
| P1 | Negative buffers make the masks overlap; large buffers produce negative NumPy bounds that wrap slices; odd buffers discard one fewer pixel than requested. | Validate numeric parameters and shape before slicing, require both retained sides, and allocate the odd extra pixel to the high-index side. Preserve the original even-buffer geometry. |
| P1 | The splitter directly overwrites either output, including its source, and can leave one newly written mask if the second save fails. | Publish one immutable directory containing both verified PNGs and a finite manifest. Refuse aliases/existing outputs, detect source changes, and clean failed staging. Retire legacy file-pair flags with migration guidance. |
| P1 | The module claims sampled patches share no pixels merely because masks are disjoint. The real sampler permits partial mask coverage. | Separate mask-pixel disjointness from unverified patch independence. A real sampler test obtains the exact same X=64..127 CT patch for both disjoint masks around X=96. Keep training sampling unchanged. |
| P2 | Three scanners and the visualizer unpack two values, while the dataset returns CT, ink, and fiber targets, so all crash on real data. | Share a strict inspection boundary that consumes the actual three-value sample and validates coordinates, tensors, masks, geometry, and read failures. |
| P2 | Scanners claim 1,000 samples even for smaller catalogs, count ink/CT outside the selected mask, and assert positive ink despite sampler fallback. | Report requested/available/actual counts, restrict statistics to requested pixels, identify catalog selection bias, and retain measured zero densities. |
| P2 | Diagnostics use hidden hardcoded CLI data paths, jittered reads, persistent shared caches, and zero fallback on read failures. | Require explicit CLI inputs, deterministic unjittered coordinates, temporary caches, strict reads, finite normalized CT, and source image hashes. Route progress to stderr for machine-readable JSON. |
| P2 | The visualizer drops a one-layer depth axis with `squeeze`, collides across fragments using the same volume basename, and writes directly to existing files. | Preserve CT dimensions, use the fragment basename for Python defaults, require explicit CLI output, stage and verify new PNGs, and embed the actual sample report. Mask labels outside the requested region. |

The initial regression run reproduced **9 failures in 5.58 s**: odd/negative/
oversized gaps, 3D and one-sided masks, source overwrite, and three real scanner
unpack failures. The unchanged visualization separately reproduced the same
sample-format failure (**1 failed, 9 deselected in 4.89 s**).

## Architecture decisions

Share inspection across all four entry points instead of changing training or
copying the sampler. Reuse existing binary PNG, model-input tensor, numeric, and
immutable-publication helpers. Scans stream bounded samples; plots retain at most
32 bounded CT patches. Masks and label planes have an explicit pixel budget,
and each CT patch has a voxel budget. No dependency or upstream source edits are
needed. Actual sampler behavior remains visible, including partial contexts and
label-conditioned fallback, rather than being rewritten into an independence
claim.

The operator workflow and CLI migration are documented in
[Spatial partitions and inspection](SPATIAL_PARTITIONS_AND_INSPECTION.md).

## Verification

Focused regression command:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_spatial_inspection_contracts.py tests/test_spatial_split_mask.py -q --no-header --tb=short
```

Captured: **80 passed in 26.26s**. This includes 78 new cases and the two existing
splitter tests. Real local dataset/CLI reads, exact gap geometry, safe publication,
masked statistics, context overlap, and read/render failures pass. The generated
one-layer toy figure was also opened and visually checked for intact CT rows,
masked labels, overlays, and coordinate titles; this is mechanical evidence.

Standard validation command:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
```

Captured: **1150 passed, 3 skipped, 1 xfailed, 9 warnings in 278.00s (0:04:38)**.
The standard workflow suite, now including spatial inspection, passes. Skips and
the expected upstream failure retain their existing conditions; warnings concern
CPU-only data-loader pinning.

Required smoke command:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
```

Captured: **8/11 passed, 3 skipped, 0 failed in 48.4s**. Imports, model/auxiliary
heads, real best-checkpoint loading (288/288 keys), augmentations, and bandit
templates pass. Two missing local-data fixtures and the optional
`batchgeneratorsv2` transform account for skips.

Documentation, claims, filing-number, and upstream-parity command:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py -q --no-header --tb=short
```

Captured: **106 passed, 16 skipped in 75.64s (0:01:15)**. Available reference and
claim guards pass; skipped checks require an absent sibling ScrollGT checkout or
external render artifacts.

After recording the results, the final reference/claim check was:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
```

Captured: **16 passed in 13.63s**. The completed report's references and claim
guards pass.

Typing command:

```bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
```

Captured: **Found 16 errors in 13 files (checked 623 source files)**. Typing remains
a failing check with the same existing diagnostics: missing YAML/requests stubs,
OpenCV overloads, augmentation slice types, loader tensor-list annotations, and
training tensor-list mean/variance calls. None are in changed files.

Lint, format, and whitespace commands:

```bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/spatial_split_mask.py scripts/dataset_inspection.py scripts/scan_dataset.py scripts/scan_val_dataset.py scripts/scan_ink_density.py scripts/visualize_training_data.py scripts/run_validation_tests.py tests/test_spatial_inspection_contracts.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/spatial_split_mask.py scripts/dataset_inspection.py scripts/scan_dataset.py scripts/scan_val_dataset.py scripts/scan_ink_density.py scripts/visualize_training_data.py scripts/run_validation_tests.py tests/test_spatial_inspection_contracts.py
git diff --check
```

Captured: **All checks passed!**, **8 files already formatted**, and no whitespace
diagnostics. No packages were installed; cached lint/typing tools ran offline.

## Edge cases considered

Odd/even/zero/negative/oversized gaps; invalid axes, fractions, booleans, shapes,
encodings, and one-sided support; pixel-budget failures; source/existing/symlink
output aliases; second-save/render failures, corrupt writes and changed inputs;
real partial-mask sampler overlap; actual/available/requested sample counts;
zero-ink fallback; labels and CT intensity outside the requested region; shallow
and oversized CT patches; nonfinite or misaligned samples; invalid coordinates;
real CT read failures; CLI calls outside the checkout; one-layer figures;
embedded PNG provenance; source-cache isolation.

## What was NOT tested

GPU inspection, full-size scrolls, retraining, historical experiment reruns,
complete CT-byte hashing, model quality, held-out lineage, or prize eligibility.
The toy images establish mechanical contracts only. Inputs must remain stable,
and artifact publication assumes serialized writers. The existing training
sampler, jitter, loss, model/evaluation math, and research claims are unchanged.

## Reviewer focus

Check exact buffer bounds and paired publication, mask-versus-context scope,
masked statistics and catalog selection bias, use of the real three-value
sample, and read-failure behavior. CLI migration is intentional; no guarantee
of patch independence is inferred from a published mask pair.
