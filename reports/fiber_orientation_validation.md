# Fiber orientation primitive: validation (August fiber-tracer step 1)

**Date:** 2026-07-29

## Why this exists

`compute_eigenvalues_3x3_batch` (validated June 2026, see
`fibers_gpu_validation_2026-06.md`) returns eigen**values** only. Those give curvature
magnitudes, which is enough for a ridge/vesselness *response*, but a tracer needs the local fiber
**tangent direction**, which is an eigen**vector**. That primitive did not exist in this codebase.

It is added as `compute_eigenvectors_3x3_batch()` plus a `fiber_direction()` convenience wrapper
in `src/vesuvius_autoresearch/fibers/detection.py`, using the same closed-form, CuPy-safe approach
as the eigenvalue solver: CuPy's batched `eigh` fails on large batches of small matrices, exactly
the regime here, so we avoid it entirely.

Method (Eberly): the eigenvector for eigenvalue L spans the null space of `A - L*I`. Two
independent rows of that matrix span its row space, so their cross product spans the null space.
All three pairwise cross products are computed and the largest-norm one is selected, which is the
numerically stable choice.

## Correctness vs `numpy.linalg.eigh`

20,000 random symmetric 3x3 matrices, float64. Eigenvectors are defined up to sign, so agreement
is measured as `|cos|` against the reference vector.

| eigenvalue index | max(1 - \|cos\|) vs `eigh` | max \|Av - λv\| | max \|‖v‖ - 1\| |
| --- | --- | --- | --- |
| 0 | 1.776e-15 | 5.842e-10 | 3.331e-16 |
| 1 | 9.992e-16 | 6.090e-10 | 3.331e-16 |
| 2 | 9.992e-16 | 2.270e-11 | 2.220e-16 |

Agreement is at float64 round-off. The defining equation `Av = λv` holds to ~6e-10, limited by the
Cardano eigenvalues it is given rather than by the eigenvector construction.

## GPU / CPU parity

Same 3x3 batch through NumPy and CuPy:

- eigenvalues: max absolute difference **3.886e-15**
- eigenvectors, all three indices: min `|cos|` between CPU and GPU results = **1.00000000**
- validity masks: **identical** on all three indices
- synthetic tube end-to-end (below): median \|x\| = **1.0** on both backends

## Degenerate handling (the part that matters for a tracer)

Repeated eigenvalues mean the eigenvector is not unique, and near-isotropic voxels have no
meaningful direction. Rather than return an arbitrary unit vector, the routine returns a boolean
`valid` mask and writes an explicit **zero** vector where invalid. This is deliberate: an
arbitrary "direction" is precisely the value a tracer would follow off a fiber and into a
neighbouring sheet, and this module has previously shipped silent-zero and constant-input NaN
bugs. Pinned by tests:

- identity-like Hessians: `valid` is False everywhere, vectors are exactly zero, no NaN
- all-zero matrices: same
- upper-triangular input (what `hessian()` actually emits) agrees with the full symmetric form

The last point is a real trap. `hessian()` fills **only the upper triangle** and leaves the
mirrored entries at zero, because the eigenvalue solver reads only `a11/a22/a33/a12/a13/a23`. Any
routine doing genuine matrix algebra must mirror first, so `symmetrize_upper()` was added and is
called internally; a test asserts both input forms give the same eigenvectors.

## End-to-end contract

A synthetic bright cylinder of radius 3 along axis 2 (x), through
`hessian()` → `fiber_direction()`: median \|x-component\| of the recovered tangent over valid core
voxels is **1.0** (test asserts > 0.95). Component order follows `hessian()`'s convention, where
index 0 is the axis-2 (x) direction, index 1 is axis-1 (y), index 2 is axis-0 (z).

`fiber_direction()` selects the **smallest-magnitude** eigenvalue rather than a fixed index, so it
stays correct for both bright and dark structures, whose Hessian sign patterns differ.

## Cost

Three eigenvector passes over 20,000 matrices: **0.017 s** on CPU, **0.043 s** on GPU. At this
batch size the GPU is slower because kernel-launch overhead dominates; the GPU path matters at
volume scale, where the tiled detectors already operate (`block_size=128`, `halo=16`).

`fiber_direction()` currently solves all three indices and then selects per voxel. That is three
times the necessary work, chosen to keep the closed form branch-free and simple. Volumes are tiled
to at most `block_size³`, so this is an acceptable trade for now; if it shows up in profiling on
real cubes, it can be replaced with a gather before the solve.

## Tests

`tests/test_fiber_orientation.py`, 10 tests, all passing. Full fiber-related suite (27 tests
across `test_fibers.py`, `test_fibers_cli.py`, `test_frangi_fiber_target.py`,
`test_lasagna_fiber_worklist.py`, and this file) passes with GPU present.
